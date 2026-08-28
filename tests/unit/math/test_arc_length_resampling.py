"""Unit contracts for FS-009 arc-length parameterization and diagnostics."""

from typing import cast

import pytest

from fourier_sketch.domain import Curve, DomainValidationError, Point2D
from fourier_sketch.math import (
    CurveSpacingMetrics,
    curve_spacing_metrics,
    resample_curve_by_arc_length,
)

pytestmark = pytest.mark.unit


def test_open_arc_length_resampling_preserves_exact_endpoints_and_uniform_spacing() -> None:
    curve = Curve(
        (Point2D(0.0, 0.0), Point2D(1.0, 0.0), Point2D(4.0, 0.0)),
        closed=False,
    )

    sampled = resample_curve_by_arc_length(curve, 5)
    metrics = curve_spacing_metrics(sampled)

    assert sampled.points == tuple(Point2D(float(index), 0.0) for index in range(5))
    assert sampled.start is curve.start
    assert sampled.end is curve.end
    assert metrics.segment_count == 4
    assert metrics.minimum_length == pytest.approx(1.0)
    assert metrics.maximum_length == pytest.approx(1.0)
    assert metrics.coefficient_of_variation == pytest.approx(0.0)


def test_closed_arc_length_includes_seam_without_repeating_first_output() -> None:
    square = Curve(
        (
            Point2D(0.0, 0.0),
            Point2D(2.0, 0.0),
            Point2D(2.0, 2.0),
            Point2D(0.0, 2.0),
        ),
        closed=True,
    )

    sampled = resample_curve_by_arc_length(square, 8)
    metrics = curve_spacing_metrics(sampled)

    assert sampled.closed is True
    assert sampled.sample_count == 8
    assert sampled.points[0] == square.points[0]
    assert sampled.points[-1] != sampled.points[0]
    assert metrics.segment_count == 8
    assert metrics.minimum_length == pytest.approx(1.0)
    assert metrics.maximum_length == pytest.approx(1.0)


@pytest.mark.parametrize(
    "curve",
    (
        Curve((Point2D(1.0, 1.0),), closed=False),
        Curve((Point2D(1.0, 1.0), Point2D(1.0, 1.0)), closed=True),
    ),
)
def test_zero_total_length_is_a_typed_failure(curve: Curve) -> None:
    with pytest.raises(DomainValidationError, match="positive finite total length"):
        resample_curve_by_arc_length(curve, 8)


@pytest.mark.parametrize("count", (0, -1, 4097, 1.5, True))
def test_arc_length_rejects_invalid_output_budget(count: object) -> None:
    curve = Curve((Point2D(0.0, 0.0), Point2D(1.0, 0.0)), closed=False)

    with pytest.raises(DomainValidationError, match="sample_count"):
        resample_curve_by_arc_length(curve, cast(int, count))


def test_spacing_metrics_distinguish_open_segments_from_closed_seam() -> None:
    points = (Point2D(0.0, 0.0), Point2D(1.0, 0.0), Point2D(1.0, 1.0))

    opened = curve_spacing_metrics(Curve(points, closed=False))
    closed = curve_spacing_metrics(Curve(points, closed=True))

    assert opened.segment_count == 2
    assert opened.total_length == pytest.approx(2.0)
    assert closed.segment_count == 3
    assert closed.total_length == pytest.approx(2.0 + 2.0**0.5)


def test_spacing_value_rejects_inconsistent_public_construction() -> None:
    with pytest.raises(DomainValidationError):
        CurveSpacingMetrics(1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)


def test_large_finite_total_does_not_overflow_target_positions() -> None:
    curve = Curve((Point2D(0.0, 0.0), Point2D(1e308, 0.0)), closed=False)

    sampled = resample_curve_by_arc_length(curve, 4)

    assert sampled.start == curve.start
    assert sampled.end == curve.end
    assert sampled.points[1].x == pytest.approx(1e308 / 3.0)
    assert sampled.points[2].x == pytest.approx((2.0 / 3.0) * 1e308)


def test_spacing_metrics_report_subnormal_mean_as_typed_failure() -> None:
    curve = Curve(
        (Point2D(0.0, 0.0), Point2D(0.0, 0.0), Point2D(5e-324, 0.0)),
        closed=False,
    )

    with pytest.raises(DomainValidationError, match="spacing mean"):
        curve_spacing_metrics(curve)
