"""Generate the canonical cross-runtime Fourier parity corpus for FS-031."""

from __future__ import annotations

import json
from math import cos, pi, sin
from pathlib import Path

from fourier_sketch.domain import Curve, Point2D, SpectrumOrdering
from fourier_sketch.math import (
    build_epicycle_chain,
    curve_to_complex_samples,
    reference_dft,
    resample_curve_by_arc_length,
    select_first,
)

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "fixtures" / "android" / "fourier-parity-v1.json"


def _periodic_points(count: int, x_radius: float, y_radius: float) -> tuple[Point2D, ...]:
    return tuple(
        Point2D(x_radius * cos(2 * pi * index / count), y_radius * sin(2 * pi * index / count))
        for index in range(count)
    )


def _case(name: str, curve: Curve) -> dict[str, object]:
    spectrum = reference_dft(curve_to_complex_samples(curve))
    checks: list[dict[str, object]] = []
    for count in sorted({1, min(5, curve.sample_count), curve.sample_count}):
        selection = select_first(spectrum, count, SpectrumOrdering.AMPLITUDE_DESCENDING)
        for time in (0.0, 0.125, 0.625):
            endpoint = build_epicycle_chain(selection, time).endpoint
            checks.append(
                {
                    "harmonic_count": count,
                    "time": time,
                    "frequencies": [item.frequency for item in selection.coefficients],
                    "endpoint": [endpoint.x, endpoint.y],
                }
            )
    return {
        "name": name,
        "points": [[point.x, point.y] for point in curve.points],
        "coefficients": [
            [item.frequency, item.real, item.imaginary] for item in spectrum.coefficients
        ],
        "endpoint_checks": checks,
    }


def main() -> None:
    open_source = Curve(
        (
            Point2D(-1.0, -0.25),
            Point2D(-0.4, 0.75),
            Point2D(0.2, -0.5),
            Point2D(0.75, 0.9),
            Point2D(1.0, 0.1),
        ),
        closed=False,
    )
    open_sampled = resample_curve_by_arc_length(open_source, 128)
    document = {
        "schema_version": 1,
        "normalization": "forward_1_over_n",
        "frequency_convention": "signed_fft_storage",
        "selection_order": "amplitude_descending_abs_frequency_signed_frequency",
        "tolerance": 1e-9,
        "cases": [
            _case("unit_circle_8", Curve(_periodic_points(8, 1.0, 1.0), closed=True)),
            _case("ellipse_16", Curve(_periodic_points(16, 1.25, 0.5), closed=True)),
            _case("open_arc_length_128", open_sampled),
        ],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
