"""FS-027 comparison over original and simplified curves using the accepted pipeline."""

from collections.abc import Callable
from dataclasses import dataclass
from math import isfinite

from fourier_sketch.domain import Curve, DomainValidationError, ReconstructionMetrics
from fourier_sketch.math import (
    DEFAULT_SIMPLIFICATION_EVALUATIONS,
    MAX_RESAMPLED_POINTS,
    MAX_SIMPLIFICATION_EVALUATIONS,
    CurveSimplificationError,
    DouglasPeuckerResult,
    SimplificationFailureCode,
    curve_to_complex_samples,
    reconstruction_metrics,
    resample_curve_by_arc_length,
    simplify_curve_douglas_peucker,
)

from .diagnostic_epicycles import EpicycleTimeline, validate_timeline_speed
from .freehand import build_freehand_timeline


@dataclass(frozen=True, slots=True)
class CurveSimplificationConfig:
    """Explicit equal-N/equal-K comparison and simplifier resource choices."""

    tolerance: float
    sample_count: int
    harmonic_count: int
    speed: float = 1.0
    max_distance_evaluations: int = DEFAULT_SIMPLIFICATION_EVALUATIONS

    def __post_init__(self) -> None:
        if (
            isinstance(self.tolerance, bool)
            or not isinstance(self.tolerance, (int, float))
            or not isfinite(float(self.tolerance))
            or self.tolerance < 0.0
        ):
            raise DomainValidationError(
                "curve simplification tolerance must be finite and non-negative"
            )
        if type(self.sample_count) is not int or not 1 <= self.sample_count <= MAX_RESAMPLED_POINTS:
            raise DomainValidationError(
                f"curve simplification sample_count must be between 1 and {MAX_RESAMPLED_POINTS}"
            )
        if (
            type(self.harmonic_count) is not int
            or not 1 <= self.harmonic_count <= self.sample_count
        ):
            raise DomainValidationError(
                "curve simplification harmonic_count must be between 1 and sample_count"
            )
        if (
            type(self.max_distance_evaluations) is not int
            or not 1 <= self.max_distance_evaluations <= MAX_SIMPLIFICATION_EVALUATIONS
        ):
            raise DomainValidationError(
                "curve simplification max_distance_evaluations is outside the work budget"
            )
        object.__setattr__(self, "tolerance", float(self.tolerance))
        object.__setattr__(self, "speed", validate_timeline_speed(self.speed))


@dataclass(frozen=True, slots=True)
class CurveSimplificationComparison:
    """Original/simplified equal-budget pipelines and explicitly labelled metrics."""

    config: CurveSimplificationConfig
    simplification: DouglasPeuckerResult
    baseline_sampled: Curve
    simplified_sampled: Curve
    baseline_timeline: EpicycleTimeline
    simplified_timeline: EpicycleTimeline
    sampled_metrics: ReconstructionMetrics
    baseline_reconstruction_metrics: ReconstructionMetrics
    simplified_reconstruction_metrics: ReconstructionMetrics

    def __post_init__(self) -> None:
        if not isinstance(self.config, CurveSimplificationConfig) or not isinstance(
            self.simplification, DouglasPeuckerResult
        ):
            raise DomainValidationError("curve simplification comparison provenance is invalid")
        if not isinstance(self.baseline_sampled, Curve) or not isinstance(
            self.simplified_sampled, Curve
        ):
            raise DomainValidationError("curve simplification comparison requires sampled curves")
        if (
            self.baseline_sampled.sample_count != self.config.sample_count
            or self.simplified_sampled.sample_count != self.config.sample_count
            or self.baseline_sampled.closed != self.simplified_sampled.closed
        ):
            raise DomainValidationError("curve simplification sampled budgets are inconsistent")
        if not isinstance(self.baseline_timeline, EpicycleTimeline) or not isinstance(
            self.simplified_timeline, EpicycleTimeline
        ):
            raise DomainValidationError("curve simplification comparison requires timelines")
        baseline = self.baseline_timeline.snapshot()
        simplified = self.simplified_timeline.snapshot()
        if (
            baseline.original != self.baseline_sampled
            or simplified.original != self.simplified_sampled
        ):
            raise DomainValidationError("curve simplification timelines must own sampled curves")
        if (
            baseline.selection.coefficient_count != self.config.harmonic_count
            or simplified.selection.coefficient_count != self.config.harmonic_count
        ):
            raise DomainValidationError("curve simplification harmonic budgets are inconsistent")
        values = (
            self.sampled_metrics,
            self.baseline_reconstruction_metrics,
            self.simplified_reconstruction_metrics,
        )
        if any(not isinstance(value, ReconstructionMetrics) for value in values):
            raise DomainValidationError("curve simplification comparison metrics are invalid")


def compare_curve_simplification(
    source: Curve,
    config: CurveSimplificationConfig,
    *,
    cancellation_check: Callable[[], bool] | None = None,
) -> CurveSimplificationComparison:
    """Build original/simplified actual timelines transactionally against one reference."""

    if not isinstance(source, Curve) or not isinstance(config, CurveSimplificationConfig):
        raise DomainValidationError("curve simplification comparison input is invalid")
    if cancellation_check is not None and not callable(cancellation_check):
        raise DomainValidationError("curve simplification cancellation_check must be callable")
    simplification = simplify_curve_douglas_peucker(
        source,
        config.tolerance,
        max_distance_evaluations=config.max_distance_evaluations,
        cancellation_check=cancellation_check,
    )
    _check_cancelled(cancellation_check)
    baseline_sampled = resample_curve_by_arc_length(source, config.sample_count)
    simplified_sampled = resample_curve_by_arc_length(
        simplification.curve,
        config.sample_count,
    )
    _check_cancelled(cancellation_check)
    baseline_timeline = build_freehand_timeline(
        baseline_sampled,
        harmonic_count=config.harmonic_count,
        speed=config.speed,
    )
    simplified_timeline = build_freehand_timeline(
        simplified_sampled,
        harmonic_count=config.harmonic_count,
        speed=config.speed,
    )
    baseline_frame = baseline_timeline.snapshot()
    simplified_frame = simplified_timeline.snapshot()
    baseline_reference = curve_to_complex_samples(baseline_sampled)
    simplified_samples = curve_to_complex_samples(simplified_sampled)
    baseline_reconstruction = curve_to_complex_samples(baseline_frame.reconstruction)
    simplified_reconstruction = curve_to_complex_samples(simplified_frame.reconstruction)
    comparison = CurveSimplificationComparison(
        config=config,
        simplification=simplification,
        baseline_sampled=baseline_sampled,
        simplified_sampled=simplified_sampled,
        baseline_timeline=baseline_timeline,
        simplified_timeline=simplified_timeline,
        sampled_metrics=reconstruction_metrics(baseline_reference, simplified_samples),
        baseline_reconstruction_metrics=reconstruction_metrics(
            baseline_reference,
            baseline_reconstruction,
        ),
        simplified_reconstruction_metrics=reconstruction_metrics(
            baseline_reference,
            simplified_reconstruction,
        ),
    )
    _check_cancelled(cancellation_check)
    return comparison


def _check_cancelled(cancellation_check: Callable[[], bool] | None) -> None:
    if cancellation_check is not None and cancellation_check():
        raise CurveSimplificationError(
            SimplificationFailureCode.CANCELLED,
            "curve simplification comparison was cancelled",
        )
