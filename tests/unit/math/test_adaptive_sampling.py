import pytest

from fourier_sketch.domain import Curve, DomainValidationError, Point2D
from fourier_sketch.math import (
    AdaptiveSamplingPolicy,
    resample_curve_adaptive,
)


def test_open_sampling_is_exact_and_preserves_endpoints() -> None:
    source = Curve((Point2D(0, 0), Point2D(1, 0), Point2D(1, 2)))
    result = resample_curve_adaptive(source, 17, curvature_weight=20)
    assert len(result.curve.points) == 17
    assert result.curve.points[0] == source.points[0]
    assert result.curve.points[-1] == source.points[-1]
    assert result.policy == AdaptiveSamplingPolicy.ADAPTIVE_WEIGHTED_ARC_LENGTH


def test_closed_cleanup_has_exact_count_without_seam_duplicate() -> None:
    source = Curve((Point2D(0, 0), Point2D(2, 0), Point2D(1, 1), Point2D(0, 0)), closed=True)
    result = resample_curve_adaptive(source, 32, curvature_weight=0)
    assert len(result.curve.points) == 32
    assert result.curve.points[0] == Point2D(0, 0)
    assert result.curve.points[-1] != result.curve.points[0]
    assert result.policy == AdaptiveSamplingPolicy.UNIFORM_ARC_LENGTH_ZERO_ADAPTIVE_SIGNAL


def test_cleanup_does_not_mutate_source_and_invalid_values_fail() -> None:
    source = Curve((Point2D(0, 0), Point2D(1, 0)))
    original = source.points
    with pytest.raises(DomainValidationError):
        resample_curve_adaptive(source, 4, curvature_weight=101)
    assert source.points == original


def test_turning_angles_are_normalized() -> None:
    result = resample_curve_adaptive(
        Curve((Point2D(0, 0), Point2D(1, 0), Point2D(1, 1))), 4, curvature_weight=1
    )
    assert result.vertex_curvatures[0] == 0.0
    assert result.vertex_curvatures[-1] == 0.0
    assert result.vertex_curvatures[1] == pytest.approx(0.5)


def test_straight_line_has_zero_turning_angle() -> None:
    result = resample_curve_adaptive(
        Curve((Point2D(0, 0), Point2D(1, 0), Point2D(2, 0))), 4, curvature_weight=10
    )
    assert result.vertex_curvatures == (0.0, 0.0, 0.0)
