"""Unit contracts for deterministic piecewise signal sampling."""

import pytest

from fourier_sketch.domain import Curve, DomainValidationError, PiecewiseCurve, Point2D
from fourier_sketch.math import PiecewiseAllocation, sample_piecewise_curve

pytestmark = pytest.mark.unit


def _line(*xs: float) -> Curve:
    return Curve(tuple(Point2D(x, 0.0) for x in xs))


def test_equal_allocation_is_exact_and_stable() -> None:
    result = sample_piecewise_curve(
        PiecewiseCurve((_line(0.0, 1.0), _line(4.0, 5.0), _line(9.0, 10.0))),
        8,
        allocation=PiecewiseAllocation.EQUAL,
    )

    assert tuple(segment.sample_count for segment in result.curve.segments) == (3, 3, 2)
    assert result.sample_count == 8


def test_proportional_allocation_favors_longer_segment() -> None:
    result = sample_piecewise_curve(
        PiecewiseCurve((_line(0.0, 1.0), _line(10.0, 14.0))),
        10,
    )

    assert tuple(segment.sample_count for segment in result.curve.segments) == (3, 7)


def test_boundaries_cover_each_signal_transition_once() -> None:
    result = sample_piecewise_curve(
        PiecewiseCurve((_line(0.0, 1.0), _line(5.0, 6.0))),
        4,
    )

    assert [(item.left_segment, item.right_segment, item.cyclic) for item in result.boundaries] == [
        (0, 1, False),
        (1, 0, True),
    ]
    assert [(item.left_sample_index, item.right_sample_index) for item in result.boundaries] == [
        (1, 2),
        (3, 0),
    ]
    assert [item.distance for item in result.boundaries] == [4.0, 6.0]


def test_closed_segment_materializes_its_seam_inside_exact_budget() -> None:
    triangle = Curve(
        (Point2D(0.0, 0.0), Point2D(1.0, 0.0), Point2D(0.0, 1.0)),
        closed=True,
    )

    result = sample_piecewise_curve(PiecewiseCurve((triangle, _line(4.0, 5.0))), 8)

    closed = result.curve.segments[0]
    assert closed.start == closed.end
    assert result.sample_count == 8
    assert result.boundaries[0].left == closed.start


def test_non_finite_derived_length_is_a_typed_error() -> None:
    huge = Curve((Point2D(-1e308, 0.0), Point2D(1e308, 0.0)))

    with pytest.raises(DomainValidationError, match="length must be finite"):
        sample_piecewise_curve(PiecewiseCurve((huge, _line(0.0, 1.0))), 8)


def test_large_finite_length_allocates_without_intermediate_overflow() -> None:
    huge = Curve((Point2D(0.0, 0.0), Point2D(1e306, 0.0)))

    result = sample_piecewise_curve(PiecewiseCurve((huge, _line(0.0, 1.0))), 4096)

    assert result.sample_count == 4096
    assert tuple(segment.sample_count for segment in result.curve.segments) == (4095, 1)


def test_isolated_segment_keeps_one_sample_beside_geometric_segment() -> None:
    isolated = Curve((Point2D(0.0, 0.0),))

    result = sample_piecewise_curve(PiecewiseCurve((isolated, _line(2.0, 3.0))), 4)

    assert tuple(segment.sample_count for segment in result.curve.segments) == (1, 3)
    assert result.sample_count == 4


def test_all_isolated_segments_use_deterministic_equal_budget() -> None:
    isolated = PiecewiseCurve(
        (Curve((Point2D(0.0, 0.0),)), Curve((Point2D(2.0, 0.0),)))
    )

    result = sample_piecewise_curve(isolated, 5)

    assert tuple(segment.sample_count for segment in result.curve.segments) == (3, 2)
    assert result.sample_count == 5


def test_each_segment_requires_one_sample() -> None:
    with pytest.raises(DomainValidationError, match="one sample per segment"):
        sample_piecewise_curve(
            PiecewiseCurve((_line(0.0, 1.0), _line(2.0, 3.0), _line(4.0, 5.0))),
            2,
        )
