"""Bounded freehand capture composed with the accepted Fourier timeline."""

from dataclasses import dataclass
from enum import StrEnum

from fourier_sketch.application.diagnostic_epicycles import EpicycleTimeline
from fourier_sketch.domain import Curve, DomainValidationError, Point2D, SpectrumOrdering
from fourier_sketch.math import (
    CurveSpacingMetrics,
    ResamplingMethod,
    cleanup_consecutive_duplicates,
    curve_spacing_metrics,
    curve_to_complex_samples,
    fft_dft,
    resample_curve_by_arc_length,
    resample_curve_by_index,
)

MAX_CAPTURE_POINTS = 10_000
DEFAULT_FREEHAND_SAMPLES = 128
DEFAULT_FREEHAND_HARMONICS = 15


class CaptureState(StrEnum):
    """Explicit lifecycle for one freehand stroke."""

    EMPTY = "empty"
    CAPTURING = "capturing"
    READY = "ready"
    LIMIT_REACHED = "limit_reached"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class FreehandCaptureSnapshot:
    """Immutable presentation-safe view of capture state."""

    state: CaptureState
    points: tuple[Point2D, ...]
    maximum_points: int

    def __post_init__(self) -> None:
        if not isinstance(self.state, CaptureState):
            raise DomainValidationError("capture state must be a CaptureState")
        if not isinstance(self.points, tuple) or any(
            not isinstance(point, Point2D) for point in self.points
        ):
            raise DomainValidationError("capture points must be a Point2D tuple")
        if (
            isinstance(self.maximum_points, bool)
            or not isinstance(self.maximum_points, int)
            or self.maximum_points < 1
            or self.maximum_points > MAX_CAPTURE_POINTS
        ):
            raise DomainValidationError("maximum_points is outside the capture budget")
        if len(self.points) > self.maximum_points:
            raise DomainValidationError("capture points exceed maximum_points")
        if self.state in {CaptureState.EMPTY, CaptureState.CANCELLED} and self.points:
            raise DomainValidationError("empty/cancelled capture state cannot contain points")
        if (
            self.state
            in {
                CaptureState.CAPTURING,
                CaptureState.READY,
                CaptureState.LIMIT_REACHED,
            }
            and not self.points
        ):
            raise DomainValidationError("active/ready capture state must contain points")
        if self.state is CaptureState.LIMIT_REACHED and len(self.points) != self.maximum_points:
            raise DomainValidationError("limit state must retain exactly maximum_points")


@dataclass(frozen=True, slots=True)
class FreehandCurveResult:
    """Validated raw/resampled curve pair with explicit baseline provenance."""

    source_curve: Curve
    sampled_curve: Curve
    captured_count: int
    cleaned_count: int
    method: ResamplingMethod = ResamplingMethod.UNIFORM_INDEX
    source_spacing: CurveSpacingMetrics | None = None
    sampled_spacing: CurveSpacingMetrics | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.source_curve, Curve) or not isinstance(self.sampled_curve, Curve):
            raise DomainValidationError("freehand result curves must be Curve values")
        if self.source_curve.closed != self.sampled_curve.closed:
            raise DomainValidationError("freehand source and sampled topology must match")
        if not isinstance(self.method, ResamplingMethod):
            raise DomainValidationError("freehand method must be a ResamplingMethod")
        if any(
            value is not None and not isinstance(value, CurveSpacingMetrics)
            for value in (self.source_spacing, self.sampled_spacing)
        ):
            raise DomainValidationError("freehand spacing must use CurveSpacingMetrics values")
        if (self.source_spacing is None) != (self.sampled_spacing is None):
            raise DomainValidationError("freehand spacing metrics must be both present or absent")
        if any(
            isinstance(value, bool) or not isinstance(value, int)
            for value in (self.captured_count, self.cleaned_count)
        ):
            raise DomainValidationError("freehand point counts must be integers")
        if (
            self.captured_count < self.cleaned_count
            or self.cleaned_count < 1
            or self.captured_count > MAX_CAPTURE_POINTS
        ):
            raise DomainValidationError("freehand point counts are inconsistent")
        if self.cleaned_count != self.source_curve.sample_count:
            raise DomainValidationError("cleaned_count must equal source curve sample_count")


class FreehandCapture:
    """Mutable pointer state with a fail-closed point budget."""

    def __init__(self, *, maximum_points: int = MAX_CAPTURE_POINTS) -> None:
        self._maximum_points = _validated_maximum_points(maximum_points)
        self._points: list[Point2D] = []
        self._state = CaptureState.EMPTY

    def snapshot(self) -> FreehandCaptureSnapshot:
        return FreehandCaptureSnapshot(
            state=self._state,
            points=tuple(self._points),
            maximum_points=self._maximum_points,
        )

    def pointer_down(self, point: Point2D) -> FreehandCaptureSnapshot:
        validated = _validated_point(point)
        self._points = [validated]
        self._state = CaptureState.CAPTURING
        return self.snapshot()

    def pointer_move(self, point: Point2D) -> FreehandCaptureSnapshot:
        validated = _validated_point(point)
        if self._state is not CaptureState.CAPTURING:
            return self.snapshot()
        if validated == self._points[-1]:
            return self.snapshot()
        if len(self._points) >= self._maximum_points:
            self._state = CaptureState.LIMIT_REACHED
            return self.snapshot()
        self._points.append(validated)
        return self.snapshot()

    def pointer_up(self) -> FreehandCaptureSnapshot:
        if self._state is CaptureState.CAPTURING:
            self._state = CaptureState.READY
        return self.snapshot()

    def cancel(self) -> FreehandCaptureSnapshot:
        self._points = []
        self._state = CaptureState.CANCELLED
        return self.snapshot()

    def reset(self) -> FreehandCaptureSnapshot:
        self._points = []
        self._state = CaptureState.EMPTY
        return self.snapshot()

    def build_curve(
        self,
        *,
        sample_count: int,
        closed: bool,
        method: ResamplingMethod = ResamplingMethod.UNIFORM_INDEX,
    ) -> FreehandCurveResult:
        if self._state is not CaptureState.READY:
            raise DomainValidationError("capture must be ready before building a curve")
        if not isinstance(closed, bool):
            raise DomainValidationError("closed must be a boolean")
        if not isinstance(method, ResamplingMethod):
            raise DomainValidationError("method must be a ResamplingMethod")
        captured = tuple(self._points)
        cleaned = cleanup_consecutive_duplicates(captured)
        if not cleaned:
            raise DomainValidationError("capture must contain at least one point")
        source = Curve(cleaned, closed=closed)
        sampled = (
            resample_curve_by_index(source, sample_count)
            if method is ResamplingMethod.UNIFORM_INDEX
            else resample_curve_by_arc_length(source, sample_count)
        )
        source_spacing, sampled_spacing = _spacing_pair(source, sampled)
        return FreehandCurveResult(
            source_curve=source,
            sampled_curve=sampled,
            captured_count=len(captured),
            cleaned_count=len(cleaned),
            method=method,
            source_spacing=source_spacing,
            sampled_spacing=sampled_spacing,
        )


def build_freehand_timeline(
    curve: Curve,
    *,
    harmonic_count: int | None = None,
    speed: float = 1.0,
) -> EpicycleTimeline:
    """Compose one validated Curve through FFT into the existing timeline contract."""
    if not isinstance(curve, Curve):
        raise DomainValidationError("curve must be a Curve")
    count = min(DEFAULT_FREEHAND_HARMONICS, curve.sample_count)
    if harmonic_count is not None:
        if isinstance(harmonic_count, bool) or not isinstance(harmonic_count, int):
            raise DomainValidationError("harmonic_count must be an integer")
        count = harmonic_count
    samples = curve_to_complex_samples(curve)
    return EpicycleTimeline(
        fft_dft(samples),
        curve,
        harmonic_count=count,
        ordering=SpectrumOrdering.AMPLITUDE_DESCENDING,
        speed=speed,
    )


def _validated_maximum_points(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise DomainValidationError("maximum_points must be an integer")
    if value < 1 or value > MAX_CAPTURE_POINTS:
        raise DomainValidationError(f"maximum_points must be between 1 and {MAX_CAPTURE_POINTS}")
    return value


def _validated_point(value: Point2D) -> Point2D:
    if not isinstance(value, Point2D):
        raise DomainValidationError("pointer value must be a Point2D")
    return value


def _spacing_pair(
    source: Curve,
    sampled: Curve,
) -> tuple[CurveSpacingMetrics | None, CurveSpacingMetrics | None]:
    if not _has_measurable_spacing(source) or not _has_measurable_spacing(sampled):
        return None, None
    try:
        return curve_spacing_metrics(source), curve_spacing_metrics(sampled)
    except DomainValidationError:
        return None, None


def _has_measurable_spacing(curve: Curve) -> bool:
    starts = curve.points if curve.closed else curve.points[:-1]
    ends = curve.points[1:] + ((curve.points[0],) if curve.closed else ())
    return any(start != end for start, end in zip(starts, ends, strict=True))
