"""Generative invariants for piecewise sample allocation."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from fourier_sketch.domain import Curve, PiecewiseCurve, Point2D
from fourier_sketch.math import PiecewiseAllocation, sample_piecewise_curve

pytestmark = pytest.mark.property


@given(
    segment_count=st.integers(min_value=1, max_value=8),
    extra=st.integers(min_value=1, max_value=64),
    allocation=st.sampled_from(tuple(PiecewiseAllocation)),
)
def test_allocation_preserves_budget_and_signal_boundary_count(
    segment_count: int,
    extra: int,
    allocation: PiecewiseAllocation,
) -> None:
    curve = PiecewiseCurve(
        tuple(
            Curve((Point2D(float(index * 3), 0.0), Point2D(float(index * 3 + index + 1), 0.0)))
            for index in range(segment_count)
        )
    )
    sample_count = segment_count + extra

    first = sample_piecewise_curve(curve, sample_count, allocation=allocation)
    second = sample_piecewise_curve(curve, sample_count, allocation=allocation)

    assert first == second
    assert first.sample_count == sample_count
    assert all(segment.sample_count >= 1 for segment in first.curve.segments)
    assert len(first.boundaries) == segment_count
    assert sum(boundary.cyclic for boundary in first.boundaries) == 1
