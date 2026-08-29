from fourier_sketch.application import (
    analyze_discontinuity_vs_continuous,
    build_discontinuous_fourier,
    compare_discontinuous_with_forced_route,
)
from fourier_sketch.domain import Curve, PiecewiseCurve, Point2D
from fourier_sketch.math import PiecewiseAllocation


def test_comparison_uses_same_k_budget() -> None:
    first = Curve((Point2D(0, 0), Point2D(1, 0)), closed=True)
    second = Curve((Point2D(3, 0), Point2D(4, 0)), closed=True)
    result = build_discontinuous_fourier(
        PiecewiseCurve((first, second)), 16, allocation=PiecewiseAllocation.EQUAL
    )
    forced = compare_discontinuous_with_forced_route(
        result, Curve(first.points + second.points, closed=True)
    )
    comparison = analyze_discontinuity_vs_continuous(result, forced, (1, 4, 16))
    assert [item.k for item in comparison.discontinuous.sweep] == [1, 4, 16]
    assert [item.k for item in comparison.continuous.sweep] == [1, 4, 16]
