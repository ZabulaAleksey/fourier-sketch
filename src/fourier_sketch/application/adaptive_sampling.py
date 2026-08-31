"""FS-028 equal-budget uniform/adaptive sampling comparison."""

from collections.abc import Callable
from dataclasses import dataclass
from math import isfinite

from fourier_sketch.domain import Curve, DomainValidationError, ReconstructionMetrics
from fourier_sketch.math import (
    MAX_RESAMPLED_POINTS,
    AdaptiveSamplingResult,
    CurveSpacingMetrics,
    curve_spacing_metrics,
    curve_to_complex_samples,
    reconstruction_metrics,
    resample_curve_adaptive,
    resample_curve_by_arc_length,
)

from .diagnostic_epicycles import EpicycleTimeline, validate_timeline_speed
from .freehand import build_freehand_timeline


@dataclass(frozen=True, slots=True)
class AdaptiveSamplingConfig:
    """Explicit equal-N/equal-K comparison choices."""

    curvature_weight: float
    sample_count: int
    harmonic_count: int
    speed: float = 1.0

    def __post_init__(self) -> None:
        if (
            isinstance(self.curvature_weight, bool)
            or not isinstance(self.curvature_weight, (int, float))
            or not isfinite(float(self.curvature_weight))
            or not 0.0 <= float(self.curvature_weight) <= 100.0
        ):
            raise DomainValidationError("adaptive curvature_weight must be between 0 and 100")
        if type(self.sample_count) is not int or not 1 <= self.sample_count <= MAX_RESAMPLED_POINTS:
            raise DomainValidationError(
                f"adaptive sample_count must be between 1 and {MAX_RESAMPLED_POINTS}"
            )
        if (
            type(self.harmonic_count) is not int
            or not 1 <= self.harmonic_count <= self.sample_count
        ):
            raise DomainValidationError(
                "adaptive harmonic_count must be between 1 and sample_count"
            )
        object.__setattr__(self, "curvature_weight", float(self.curvature_weight))
        object.__setattr__(self, "speed", validate_timeline_speed(self.speed))


@dataclass(frozen=True, slots=True)
class AdaptiveSamplingComparison:
    """Two actual equal-budget pipelines with one uniform reference."""

    config: AdaptiveSamplingConfig
    adaptive: AdaptiveSamplingResult
    uniform_sampled: Curve
    uniform_timeline: EpicycleTimeline
    adaptive_timeline: EpicycleTimeline
    uniform_spacing: CurveSpacingMetrics | None
    adaptive_spacing: CurveSpacingMetrics | None
    sampled_metrics: ReconstructionMetrics
    uniform_reconstruction_metrics: ReconstructionMetrics
    adaptive_reconstruction_metrics: ReconstructionMetrics

    def __post_init__(self) -> None:
        if not isinstance(self.config, AdaptiveSamplingConfig) or not isinstance(
            self.adaptive, AdaptiveSamplingResult
        ):
            raise DomainValidationError("adaptive comparison provenance is invalid")
        if not isinstance(self.uniform_sampled, Curve):
            raise DomainValidationError("adaptive comparison requires a uniform Curve")
        if (
            self.uniform_sampled.sample_count != self.config.sample_count
            or self.adaptive.curve.sample_count != self.config.sample_count
            or self.uniform_sampled.closed != self.adaptive.curve.closed
        ):
            raise DomainValidationError("adaptive comparison sample budgets are inconsistent")
        uniform = self.uniform_timeline.snapshot()
        adaptive = self.adaptive_timeline.snapshot()
        if uniform.original != self.uniform_sampled or adaptive.original != self.adaptive.curve:
            raise DomainValidationError("adaptive comparison timelines own different curves")
        if (
            uniform.selection.coefficient_count != self.config.harmonic_count
            or adaptive.selection.coefficient_count != self.config.harmonic_count
        ):
            raise DomainValidationError("adaptive comparison harmonic budgets are inconsistent")
        metrics = (
            self.sampled_metrics,
            self.uniform_reconstruction_metrics,
            self.adaptive_reconstruction_metrics,
        )
        if any(not isinstance(value, ReconstructionMetrics) for value in metrics):
            raise DomainValidationError("adaptive comparison metrics are invalid")


def compare_adaptive_sampling(
    source: Curve,
    config: AdaptiveSamplingConfig,
    *,
    cancellation_check: Callable[[], bool] | None = None,
) -> AdaptiveSamplingComparison:
    """Build uniform/adaptive actual timelines transactionally."""

    if not isinstance(source, Curve) or not isinstance(config, AdaptiveSamplingConfig):
        raise DomainValidationError("adaptive comparison input is invalid")
    if cancellation_check is not None and not callable(cancellation_check):
        raise DomainValidationError("adaptive cancellation_check must be callable")
    _check_cancelled(cancellation_check)
    uniform_sampled = resample_curve_by_arc_length(source, config.sample_count)
    adaptive = resample_curve_adaptive(
        source,
        config.sample_count,
        curvature_weight=config.curvature_weight,
    )
    _check_cancelled(cancellation_check)
    uniform_timeline = build_freehand_timeline(
        uniform_sampled,
        harmonic_count=config.harmonic_count,
        speed=config.speed,
    )
    adaptive_timeline = build_freehand_timeline(
        adaptive.curve,
        harmonic_count=config.harmonic_count,
        speed=config.speed,
    )
    uniform_frame = uniform_timeline.snapshot()
    adaptive_frame = adaptive_timeline.snapshot()
    reference = curve_to_complex_samples(uniform_sampled)
    comparison = AdaptiveSamplingComparison(
        config=config,
        adaptive=adaptive,
        uniform_sampled=uniform_sampled,
        uniform_timeline=uniform_timeline,
        adaptive_timeline=adaptive_timeline,
        uniform_spacing=_spacing_or_none(uniform_sampled),
        adaptive_spacing=_spacing_or_none(adaptive.curve),
        sampled_metrics=reconstruction_metrics(
            reference,
            curve_to_complex_samples(adaptive.curve),
        ),
        uniform_reconstruction_metrics=reconstruction_metrics(
            reference,
            curve_to_complex_samples(uniform_frame.reconstruction),
        ),
        adaptive_reconstruction_metrics=reconstruction_metrics(
            reference,
            curve_to_complex_samples(adaptive_frame.reconstruction),
        ),
    )
    _check_cancelled(cancellation_check)
    return comparison


def _spacing_or_none(curve: Curve) -> CurveSpacingMetrics | None:
    try:
        return curve_spacing_metrics(curve)
    except DomainValidationError:
        return None


def _check_cancelled(cancellation_check: Callable[[], bool] | None) -> None:
    if cancellation_check is not None and cancellation_check():
        raise DomainValidationError("adaptive sampling comparison was cancelled")
