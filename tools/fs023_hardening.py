"""Record reproducible FS-023 numerical, memory and offscreen paint evidence."""

from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import subprocess
import sys
import tracemalloc
from importlib.metadata import version
from math import cos, pi, sin
from pathlib import Path
from time import perf_counter
from typing import Any

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

from fourier_sketch.application import build_freehand_timeline
from fourier_sketch.domain import Curve, Point2D
from fourier_sketch.math import fft_dft, idft
from fourier_sketch.presentation import Translator
from fourier_sketch.ui.desktop import DesktopWindow, EpicycleCanvas

FFT_SAMPLE_COUNT = 65_536
STRESS_HARMONICS = 4096
FFT_SECONDS_CATASTROPHIC_LIMIT = 10.0
TIMELINE_SECONDS_CATASTROPHIC_LIMIT = 2.0
PAINT_SECONDS_CATASTROPHIC_LIMIT = 0.5
CANCEL_REQUEST_SECONDS_CATASTROPHIC_LIMIT = 0.25
PEAK_PYTHON_BYTES_LIMIT = 256 * 1024 * 1024
PARITY_TOLERANCE = 2e-10


def _signal(sample_count: int) -> tuple[complex, ...]:
    return tuple(
        complex(
            1.25 * cos(2.0 * pi * 7 * index / sample_count)
            + 1e-9 * cos(2.0 * pi * 131 * index / sample_count),
            0.75 * sin(2.0 * pi * 11 * index / sample_count),
        )
        for index in range(sample_count)
    )


def _git_value(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip() if completed.returncode == 0 else "unavailable"


def _paint_seconds(frame: Any, *, repeats: int = 5) -> float:
    app = QApplication.instance() or QApplication([])
    canvas = EpicycleCanvas(Translator("en"))
    canvas.resize(1280, 800)
    canvas.set_frame(frame)
    image = QImage(1280, 800, QImage.Format.Format_ARGB32)
    durations: list[float] = []
    for _ in range(repeats):
        started = perf_counter()
        canvas.render(image)
        app.processEvents()
        durations.append(perf_counter() - started)
    canvas.close()
    return statistics.median(durations)


def _cancel_request_seconds() -> float:
    class _RunningJob:
        def __init__(self) -> None:
            self.interruption_requested = False

        def isRunning(self) -> bool:
            return True

        def requestInterruption(self) -> None:
            self.interruption_requested = True

    window = DesktopWindow()
    job = _RunningJob()
    window._job = job  # type: ignore[assignment]
    started = perf_counter()
    window._cancel_current_job()
    elapsed = perf_counter() - started
    if not job.interruption_requested or window._job is not job:
        raise RuntimeError("cancel request lost ownership or did not request interruption")
    window._job = None
    window.close()
    return elapsed


def collect_evidence() -> dict[str, Any]:
    samples = _signal(FFT_SAMPLE_COUNT)
    tracemalloc.start()
    started = perf_counter()
    reconstructed = idft(fft_dft(samples))
    fft_seconds = perf_counter() - started
    _current, peak_python_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    max_round_trip_error = max(
        abs(expected - actual) for expected, actual in zip(samples, reconstructed, strict=True)
    )

    stress_samples = _signal(STRESS_HARMONICS)
    curve = Curve(
        tuple(Point2D(value.real, value.imag) for value in stress_samples),
        closed=True,
    )
    started = perf_counter()
    timeline = build_freehand_timeline(curve, harmonic_count=STRESS_HARMONICS)
    stress_timeline_seconds = perf_counter() - started
    stress_frame = timeline.snapshot()
    stress_paint_seconds = _paint_seconds(stress_frame)
    cancel_request_seconds = _cancel_request_seconds()

    default_timeline = build_freehand_timeline(curve)
    default_paint_seconds = _paint_seconds(default_timeline.snapshot())
    checks = {
        "round_trip_parity": max_round_trip_error <= PARITY_TOLERANCE,
        "python_peak_allocation": peak_python_bytes <= PEAK_PYTHON_BYTES_LIMIT,
        "fft_catastrophic_regression": fft_seconds <= FFT_SECONDS_CATASTROPHIC_LIMIT,
        "timeline_catastrophic_regression": (
            stress_timeline_seconds <= TIMELINE_SECONDS_CATASTROPHIC_LIMIT
        ),
        "paint_catastrophic_regression": stress_paint_seconds <= PAINT_SECONDS_CATASTROPHIC_LIMIT,
        "cancel_request_catastrophic_regression": (
            cancel_request_seconds <= CANCEL_REQUEST_SECONDS_CATASTROPHIC_LIMIT
        ),
    }
    return {
        "schema": "fourier-sketch.fs023-hardening",
        "version": 1,
        "environment": {
            "platform": platform.platform(),
            "processor": platform.processor(),
            "python": sys.version,
            "numpy": version("numpy"),
            "pyside6": version("pyside6"),
            "commit": _git_value("rev-parse", "HEAD"),
            "working_tree": _git_value("status", "--short"),
        },
        "budgets": {
            "fft_seconds_catastrophic_limit": FFT_SECONDS_CATASTROPHIC_LIMIT,
            "timeline_seconds_catastrophic_limit": TIMELINE_SECONDS_CATASTROPHIC_LIMIT,
            "paint_seconds_catastrophic_limit": PAINT_SECONDS_CATASTROPHIC_LIMIT,
            "cancel_request_seconds_catastrophic_limit": (
                CANCEL_REQUEST_SECONDS_CATASTROPHIC_LIMIT
            ),
            "peak_python_bytes_limit": PEAK_PYTHON_BYTES_LIMIT,
            "parity_tolerance": PARITY_TOLERANCE,
        },
        "measurements": {
            "fft_sample_count": FFT_SAMPLE_COUNT,
            "fft_round_trip_seconds": fft_seconds,
            "fft_round_trip_max_error": max_round_trip_error,
            "peak_python_bytes": peak_python_bytes,
            "stress_harmonics": STRESS_HARMONICS,
            "stress_timeline_seconds": stress_timeline_seconds,
            "default_paint_median_seconds": default_paint_seconds,
            "stress_paint_median_seconds": stress_paint_seconds,
            "cancel_request_seconds": cancel_request_seconds,
        },
        "checks": checks,
        "passed": all(checks.values()),
        "caveats": [
            "tracemalloc measures Python-managed allocations, not every native NumPy/Qt allocation",
            (
                "Qt paint evidence uses the offscreen plugin and is not visible Windows GUI/DPI "
                "evidence"
            ),
            (
                "wall-clock limits catch catastrophic regressions and are not product "
                "performance claims"
            ),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    options = parser.parse_args()
    evidence = collect_evidence()
    rendered = json.dumps(evidence, ensure_ascii=False, indent=2)
    if options.output is None:
        print(rendered)
    else:
        options.output.parent.mkdir(parents=True, exist_ok=True)
        options.output.write_text(rendered + "\n", encoding="utf-8")
        print(options.output)
    return 0 if evidence["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
