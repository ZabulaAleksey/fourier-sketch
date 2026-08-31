"""Known-fixture and failure contracts for bounded Douglas-Peucker simplification."""

from typing import cast

import pytest

from fourier_sketch.domain import Curve, DomainValidationError, Point2D
from fourier_sketch.math import (
    CLOSED_ANCHOR_POLICY,
    CurveSimplificationError,
    SimplificationFailureCode,
    simplify_curve_douglas_peucker,
)


def _curve(*coordinates: tuple[float, float], closed: bool = False) -> Curve:
    return Curve(tuple(Point2D(x, y) for x, y in coordinates), closed=closed)


def test_open_curve_preserves_endpoints_and_respects_tolerance() -> None:
    source = _curve((0.0, 0.0), (1.0, 0.1), (2.0, 0.0))

    reduced = simplify_curve_douglas_peucker(source, 0.1)
    retained = simplify_curve_douglas_peucker(source, 0.09)

    assert reduced.source is source
    assert reduced.retained_indices == (0, 2)
    assert reduced.curve.points == (source.start, source.end)
    assert reduced.metrics.maximum_segment_deviation == pytest.approx(0.1)
    assert retained.retained_indices == (0, 1, 2)
    assert source.sample_count == 3


def test_zero_tolerance_removes_only_exact_collinear_and_duplicate_interior_points() -> None:
    source = _curve(
        (0.0, 0.0),
        (1.0, 0.0),
        (1.0, 0.0),
        (2.0, 0.0),
        (2.0, 1.0),
    )

    result = simplify_curve_douglas_peucker(source, 0.0)

    assert result.retained_indices == (0, 3, 4)
    assert result.metrics.maximum_segment_deviation == 0.0


def test_closed_curve_uses_deterministic_anchor_and_never_adds_duplicate_seam() -> None:
    source = _curve(
        (0.0, 0.0),
        (0.5, 0.0),
        (1.0, 0.0),
        (1.0, 1.0),
        (0.0, 1.0),
        (0.0, 0.5),
        closed=True,
    )

    result = simplify_curve_douglas_peucker(source, 0.01)

    assert result.curve.closed
    assert result.retained_indices == (0, 2, 3, 4)
    assert result.curve.points[0] == source.points[0]
    assert result.curve.points[-1] != result.curve.points[0]
    assert result.closed_anchor_policy == CLOSED_ANCHOR_POLICY
    assert result.metrics.maximum_segment_deviation <= result.tolerance


def test_explicit_closed_duplicate_seam_is_canonicalized_as_source_subsequence() -> None:
    source = _curve(
        (0.0, 0.0),
        (1.0, 0.0),
        (1.0, 1.0),
        (0.0, 1.0),
        (0.0, 0.0),
        closed=True,
    )

    result = simplify_curve_douglas_peucker(source, 0.0)

    assert result.retained_indices == (0, 1, 2, 3)
    assert result.metrics.source_point_count == 5
    assert result.metrics.simplified_point_count == 4
    assert result.curve.points[-1] != result.curve.points[0]


def test_collinear_closed_backtracking_preserves_zero_tolerance() -> None:
    source = _curve(
        (0.0, 2.0),
        (0.0, 0.5),
        (0.0, 1.0),
        (0.0, 0.0),
        closed=True,
    )

    result = simplify_curve_douglas_peucker(source, 0.0)

    assert result.retained_indices == (0, 1, 2, 3)
    assert result.metrics.maximum_segment_deviation == 0.0


@pytest.mark.parametrize(
    "source",
    [
        _curve((1.0, 2.0)),
        _curve((0.0, 0.0), (1.0, 1.0)),
        _curve((0.0, 0.0), (1.0, 0.0), (0.0, 1.0), closed=True),
    ],
)
def test_small_curves_are_stable(source: Curve) -> None:
    result = simplify_curve_douglas_peucker(source, 100.0)
    assert result.curve == source
    assert result.retained_indices == tuple(range(source.sample_count))


@pytest.mark.parametrize("tolerance", [-1.0, float("nan"), float("inf"), True, "1"])
def test_invalid_tolerance_is_rejected(tolerance: object) -> None:
    with pytest.raises(DomainValidationError, match="tolerance"):
        simplify_curve_douglas_peucker(
            _curve((0.0, 0.0), (1.0, 1.0)),
            cast(float, tolerance),
        )


def test_budget_and_cancellation_fail_without_partial_result() -> None:
    source = _curve(*((float(index), float(index % 2)) for index in range(20)))

    with pytest.raises(CurveSimplificationError) as budget_error:
        simplify_curve_douglas_peucker(source, 0.0, max_distance_evaluations=1)
    assert budget_error.value.code is SimplificationFailureCode.RESOURCE_LIMIT

    with pytest.raises(CurveSimplificationError) as cancelled:
        simplify_curve_douglas_peucker(source, 0.0, cancellation_check=lambda: True)
    assert cancelled.value.code is SimplificationFailureCode.CANCELLED
    assert source.sample_count == 20
