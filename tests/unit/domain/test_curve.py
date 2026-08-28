"""Unit contracts for Curve and PiecewiseCurve."""

from typing import cast

import pytest

from fourier_sketch.domain import Curve, DomainValidationError, PiecewiseCurve, Point2D

pytestmark = pytest.mark.unit


def test_curve_preserves_order_and_explicit_closed_semantics() -> None:
    first = Point2D(0.0, 0.0)
    second = Point2D(1.0, 2.0)
    curve = Curve(points=(first, second), closed=True)

    assert curve.points == (first, second)
    assert curve.start == first
    assert curve.end == second
    assert curve.sample_count == 2
    assert curve.closed is True


def test_curve_accepts_a_single_point() -> None:
    point = Point2D(4.0, -2.0)

    assert Curve(points=(point,)).sample_count == 1


def test_curve_rejects_empty_points() -> None:
    with pytest.raises(DomainValidationError, match="at least one point"):
        Curve(points=())


def test_curve_rejects_non_point_members() -> None:
    invalid_point = cast(Point2D, object())

    with pytest.raises(DomainValidationError, match="Point2D"):
        Curve(points=(invalid_point,))


def test_curve_and_piecewise_curve_reject_malformed_collections_with_typed_error() -> None:
    invalid_points = cast(tuple[Point2D, ...], None)
    invalid_segments = cast(tuple[Curve, ...], None)

    with pytest.raises(DomainValidationError, match="points"):
        Curve(points=invalid_points)
    with pytest.raises(DomainValidationError, match="segments"):
        PiecewiseCurve(segments=invalid_segments)


def test_curve_requires_boolean_closed_flag() -> None:
    invalid_flag = cast(bool, 1)

    with pytest.raises(DomainValidationError, match="boolean"):
        Curve(points=(Point2D(0.0, 0.0),), closed=invalid_flag)


def test_piecewise_curve_keeps_independent_segments_without_bridge_samples() -> None:
    first = Curve(points=(Point2D(0.0, 0.0), Point2D(1.0, 0.0)))
    second = Curve(points=(Point2D(10.0, 0.0), Point2D(11.0, 0.0)))
    piecewise = PiecewiseCurve(segments=(first, second))

    assert piecewise.segments == (first, second)
    assert piecewise.segment_count == 2
    assert piecewise.sample_count == 4
    assert first.end != second.start


def test_piecewise_curve_rejects_empty_or_invalid_segments() -> None:
    with pytest.raises(DomainValidationError, match="at least one segment"):
        PiecewiseCurve(segments=())

    invalid_segment = cast(Curve, object())
    with pytest.raises(DomainValidationError, match="Curve values"):
        PiecewiseCurve(segments=(invalid_segment,))
