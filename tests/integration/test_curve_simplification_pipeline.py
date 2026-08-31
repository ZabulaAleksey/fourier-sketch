"""Original/simplified equal-budget Fourier pipeline integration for FS-027."""

from math import cos, pi, sin

from fourier_sketch.application import (
    CurveSimplificationConfig,
    compare_curve_simplification,
)
from fourier_sketch.domain import Curve, Point2D


def test_comparison_uses_same_sample_harmonic_budget_and_baseline_reference() -> None:
    source = Curve(
        tuple(
            Point2D(
                (1.0 + 0.08 * cos(12.0 * pi * index / 128))
                * cos(2.0 * pi * index / 128),
                (1.0 + 0.08 * cos(12.0 * pi * index / 128))
                * sin(2.0 * pi * index / 128),
            )
            for index in range(128)
        ),
        closed=True,
    )
    source_before = source.points

    comparison = compare_curve_simplification(
        source,
        CurveSimplificationConfig(
            tolerance=0.02,
            sample_count=64,
            harmonic_count=16,
            speed=0.5,
        ),
    )

    assert comparison.simplification.source is source
    assert comparison.simplification.curve.sample_count < source.sample_count
    assert comparison.baseline_sampled.sample_count == 64
    assert comparison.simplified_sampled.sample_count == 64
    baseline = comparison.baseline_timeline.snapshot()
    simplified = comparison.simplified_timeline.snapshot()
    assert baseline.selection.coefficient_count == 16
    assert simplified.selection.coefficient_count == 16
    assert baseline.speed == simplified.speed == 0.5
    assert baseline.trace[-1] == baseline.chain.endpoint
    assert simplified.trace[-1] == simplified.chain.endpoint
    assert comparison.sampled_metrics.rmse >= 0.0
    assert comparison.baseline_reconstruction_metrics.rmse >= 0.0
    assert comparison.simplified_reconstruction_metrics.rmse >= 0.0
    assert source.points is source_before
