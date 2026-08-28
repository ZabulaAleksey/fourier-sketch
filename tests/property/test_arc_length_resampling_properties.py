"""Property evidence for bounded open arc-length interpolation."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from fourier_sketch.domain import Curve, Point2D
from fourier_sketch.math import curve_spacing_metrics, resample_curve_by_arc_length

pytestmark = pytest.mark.property


@given(
    lengths=st.lists(
        st.floats(min_value=0.01, max_value=100.0, allow_nan=False, allow_infinity=False),
        min_size=1,
        max_size=20,
    ),
    sample_count=st.integers(min_value=2, max_value=128),
)
def test_open_straight_polyline_preserves_order_endpoints_and_uniform_spacing(
    lengths: list[float],
    sample_count: int,
) -> None:
    positions = [0.0]
    for length in lengths:
        positions.append(positions[-1] + length)
    curve = Curve(tuple(Point2D(position, 0.0) for position in positions), closed=False)

    sampled = resample_curve_by_arc_length(curve, sample_count)
    metrics = curve_spacing_metrics(sampled)

    assert sampled.start == curve.start
    assert sampled.end == curve.end
    assert all(
        left.x <= right.x for left, right in zip(sampled.points, sampled.points[1:], strict=False)
    )
    assert metrics.coefficient_of_variation <= 1e-10
