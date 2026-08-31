"""Uniform/adaptive equal-budget Fourier pipeline integration for FS-028."""

from fourier_sketch.application import (
    AdaptiveSamplingConfig,
    compare_adaptive_sampling,
)
from fourier_sketch.domain import Curve, Point2D
from fourier_sketch.math import AdaptiveSamplingPolicy


def test_high_curvature_curve_reaches_equal_budget_actual_timelines() -> None:
    source = Curve(
        (
            Point2D(0.0, 0.0),
            Point2D(4.0, 0.0),
            Point2D(4.0, 0.5),
            Point2D(4.5, 0.5),
            Point2D(4.5, 4.0),
        ),
        closed=False,
    )
    before = source.points

    comparison = compare_adaptive_sampling(
        source,
        AdaptiveSamplingConfig(
            curvature_weight=20.0,
            sample_count=64,
            harmonic_count=12,
            speed=0.5,
        ),
    )

    assert comparison.adaptive.source is source
    assert comparison.adaptive.policy == AdaptiveSamplingPolicy.ADAPTIVE_WEIGHTED_ARC_LENGTH
    assert comparison.uniform_sampled.sample_count == 64
    assert comparison.adaptive.curve.sample_count == 64
    uniform = comparison.uniform_timeline.snapshot()
    adaptive = comparison.adaptive_timeline.snapshot()
    assert uniform.selection.coefficient_count == adaptive.selection.coefficient_count == 12
    assert uniform.speed == adaptive.speed == 0.5
    assert uniform.trace[-1] == uniform.chain.endpoint
    assert adaptive.trace[-1] == adaptive.chain.endpoint
    assert comparison.sampled_metrics.rmse >= 0.0
    assert comparison.uniform_reconstruction_metrics.rmse >= 0.0
    assert comparison.adaptive_reconstruction_metrics.rmse >= 0.0
    assert source.points is before
