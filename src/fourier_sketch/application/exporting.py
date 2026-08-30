"""Versioned local export contracts over existing immutable Fourier state."""

from __future__ import annotations

import csv
import json
import os
import tempfile
from collections.abc import Callable, Iterator
from dataclasses import dataclass, replace
from enum import StrEnum
from io import StringIO
from pathlib import Path

from fourier_sketch.domain import CoefficientSelection, Curve, DomainValidationError, Point2D
from fourier_sketch.math import build_epicycle_chain

from .diagnostic_epicycles import EpicycleFrame, TimelineState
from .local_paths import validate_local_path

EXPORT_SCHEMA_VERSION = 1
MIN_GIF_FRAMES = 2
MAX_GIF_FRAMES = 120
MIN_GIF_FRAME_DURATION_MS = 20
MAX_GIF_FRAME_DURATION_MS = 1000


class ExportFormat(StrEnum):
    """Formats exposed by the FS-022 desktop export surface."""

    CURVE_JSON = "curve_json"
    CURVE_CSV = "curve_csv"
    COEFFICIENTS_JSON = "coefficients_json"
    COEFFICIENTS_CSV = "coefficients_csv"
    RECONSTRUCTION_PNG = "reconstruction_png"
    SPECTRUM_PNG = "spectrum_png"
    GIF = "gif"
    MP4 = "mp4"


class ExportCancelled(DomainValidationError):
    """A cooperative export cancellation left no published artifact."""


class ExportUnavailable(DomainValidationError):
    """An optional export backend is unavailable without silent substitution."""


@dataclass(frozen=True, slots=True)
class ExportCapability:
    """Explicit availability result for an optional export format."""

    available: bool
    reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.available, bool):
            raise DomainValidationError("capability availability must be boolean")
        if not isinstance(self.reason, str) or not self.reason:
            raise DomainValidationError("capability reason must be a non-empty string")


@dataclass(frozen=True, slots=True)
class AnimationExportPlan:
    """Bounded parameters for replaying one accepted selection as export frames."""

    frame: EpicycleFrame
    frame_count: int = 60
    frame_duration_ms: int = 33

    def __post_init__(self) -> None:
        if not isinstance(self.frame, EpicycleFrame):
            raise DomainValidationError("animation plan frame must be an EpicycleFrame")
        if (
            isinstance(self.frame_count, bool)
            or not isinstance(self.frame_count, int)
            or not MIN_GIF_FRAMES <= self.frame_count <= MAX_GIF_FRAMES
        ):
            raise DomainValidationError(
                f"frame_count must be between {MIN_GIF_FRAMES} and {MAX_GIF_FRAMES}"
            )
        if (
            isinstance(self.frame_duration_ms, bool)
            or not isinstance(self.frame_duration_ms, int)
            or not MIN_GIF_FRAME_DURATION_MS <= self.frame_duration_ms <= MAX_GIF_FRAME_DURATION_MS
        ):
            raise DomainValidationError(
                "frame_duration_ms must be between "
                f"{MIN_GIF_FRAME_DURATION_MS} and {MAX_GIF_FRAME_DURATION_MS}"
            )


def mp4_capability() -> ExportCapability:
    """Return the reviewed capability truth without probing or invoking a subprocess."""

    return ExportCapability(False, "no reviewed MP4 backend is configured")


def iter_animation_frames(
    plan: AnimationExportPlan,
    *,
    cancelled: Callable[[], bool] | None = None,
) -> Iterator[EpicycleFrame]:
    """Yield frames from the accepted selection and actual chain endpoint semantics."""

    if not isinstance(plan, AnimationExportPlan):
        raise DomainValidationError("plan must be an AnimationExportPlan")
    if cancelled is not None and not callable(cancelled):
        raise DomainValidationError("cancelled must be callable")
    trace: list[Point2D] = []
    time_step = plan.frame_duration_ms / 1000.0 * plan.frame.speed
    for index in range(plan.frame_count):
        if cancelled is not None and cancelled():
            raise ExportCancelled("animation export was cancelled")
        chain = build_epicycle_chain(
            plan.frame.selection,
            plan.frame.chain.time + index * time_step,
            origin=plan.frame.chain.origin,
        )
        trace.append(chain.endpoint)
        yield replace(
            plan.frame,
            chain=chain,
            trace=tuple(trace),
            timeline_state=TimelineState.PAUSED,
        )


def export_curve_data(
    curve: Curve,
    output: Path,
    *,
    format: ExportFormat,
    overwrite: bool = False,
    cancelled: Callable[[], bool] | None = None,
) -> Path:
    """Serialize one Curve with an explicit schema/version and atomic publication."""

    if not isinstance(curve, Curve):
        raise DomainValidationError("curve export requires a Curve")
    if format is ExportFormat.CURVE_JSON:
        payload = {
            "schema": "fourier-sketch.curve",
            "version": EXPORT_SCHEMA_VERSION,
            "closed": curve.closed,
            "sample_count": curve.sample_count,
            "points": [{"x": point.x, "y": point.y} for point in curve.points],
        }
        text = json.dumps(payload, ensure_ascii=True, separators=(",", ":")) + "\n"
        suffix = ".json"
    elif format is ExportFormat.CURVE_CSV:
        stream = StringIO(newline="")
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(("schema", "version", "closed", "sample_count", "index", "x", "y"))
        for index, point in enumerate(curve.points):
            writer.writerow(
                (
                    "fourier-sketch.curve",
                    EXPORT_SCHEMA_VERSION,
                    str(curve.closed).lower(),
                    curve.sample_count,
                    index,
                    repr(point.x),
                    repr(point.y),
                )
            )
        text = stream.getvalue()
        suffix = ".csv"
    else:
        raise DomainValidationError("curve export format must be curve_json or curve_csv")
    return _atomic_write(
        output,
        text.encode("utf-8"),
        suffix=suffix,
        overwrite=overwrite,
        cancelled=cancelled,
    )


def export_coefficient_data(
    selection: CoefficientSelection,
    output: Path,
    *,
    format: ExportFormat,
    overwrite: bool = False,
    cancelled: Callable[[], bool] | None = None,
) -> Path:
    """Serialize the current ordered coefficient selection with provenance."""

    if not isinstance(selection, CoefficientSelection):
        raise DomainValidationError("coefficient export requires a CoefficientSelection")
    rows = [
        {
            "frequency": coefficient.frequency,
            "real": coefficient.real,
            "imaginary": coefficient.imaginary,
            "amplitude": coefficient.amplitude,
            "phase": coefficient.phase,
        }
        for coefficient in selection.coefficients
    ]
    if format is ExportFormat.COEFFICIENTS_JSON:
        payload = {
            "schema": "fourier-sketch.coefficient-selection",
            "version": EXPORT_SCHEMA_VERSION,
            "sample_count": selection.sample_count,
            "coefficient_count": selection.coefficient_count,
            "ordering": selection.ordering.value,
            "coefficients": rows,
        }
        text = json.dumps(payload, ensure_ascii=True, separators=(",", ":")) + "\n"
        suffix = ".json"
    elif format is ExportFormat.COEFFICIENTS_CSV:
        stream = StringIO(newline="")
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(
            (
                "schema",
                "version",
                "sample_count",
                "coefficient_count",
                "ordering",
                "index",
                "frequency",
                "real",
                "imaginary",
                "amplitude",
                "phase",
            )
        )
        for index, row in enumerate(rows):
            writer.writerow(
                (
                    "fourier-sketch.coefficient-selection",
                    EXPORT_SCHEMA_VERSION,
                    selection.sample_count,
                    selection.coefficient_count,
                    selection.ordering.value,
                    index,
                    row["frequency"],
                    repr(row["real"]),
                    repr(row["imaginary"]),
                    repr(row["amplitude"]),
                    repr(row["phase"]),
                )
            )
        text = stream.getvalue()
        suffix = ".csv"
    else:
        raise DomainValidationError(
            "coefficient export format must be coefficients_json or coefficients_csv"
        )
    return _atomic_write(
        output,
        text.encode("utf-8"),
        suffix=suffix,
        overwrite=overwrite,
        cancelled=cancelled,
    )


def atomic_publish_bytes(
    output: Path,
    payload: bytes,
    *,
    suffix: str,
    overwrite: bool = False,
    cancelled: Callable[[], bool] | None = None,
) -> Path:
    """Publish already encoded bytes through the shared FS-022 atomic boundary."""

    if not isinstance(payload, bytes) or not payload:
        raise DomainValidationError("export payload must be non-empty bytes")
    return _atomic_write(
        output,
        payload,
        suffix=suffix,
        overwrite=overwrite,
        cancelled=cancelled,
    )


def _atomic_write(
    output: Path,
    payload: bytes,
    *,
    suffix: str,
    overwrite: bool,
    cancelled: Callable[[], bool] | None,
) -> Path:
    validate_local_path(output, field_name="export output")
    if not isinstance(suffix, str) or not suffix.startswith("."):
        raise DomainValidationError("export suffix must start with a dot")
    if output.suffix.lower() != suffix:
        raise DomainValidationError(f"export output must use the {suffix} extension")
    if type(overwrite) is not bool:
        raise DomainValidationError("overwrite must be a boolean")
    if cancelled is not None and not callable(cancelled):
        raise DomainValidationError("cancelled must be callable")
    if not output.parent.is_dir():
        raise DomainValidationError("export output parent directory must exist")
    if output.exists() and not overwrite:
        raise FileExistsError(output.name)

    temporary: Path | None = None
    try:
        _raise_if_cancelled(cancelled)
        with tempfile.NamedTemporaryFile(
            prefix=f".{output.stem}.", suffix=".tmp", dir=output.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        _raise_if_cancelled(cancelled)
        if overwrite:
            os.replace(temporary, output)
            temporary = None
        else:
            os.link(temporary, output)
        return output
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def _raise_if_cancelled(cancelled: Callable[[], bool] | None) -> None:
    if cancelled is not None and cancelled():
        raise ExportCancelled("export was cancelled before publication")
