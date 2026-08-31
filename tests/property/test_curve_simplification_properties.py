"""Generative invariants for deterministic curve simplification."""

from hypothesis import given, settings
from hypothesis import strategies as st

from fourier_sketch.domain import Curve, Point2D
from fourier_sketch.math import simplify_curve_douglas_peucker


@settings(max_examples=60, deadline=None)
@given(
    coordinates=st.lists(
        st.tuples(
            st.floats(-100.0, 100.0, allow_nan=False, allow_infinity=False),
            st.floats(-100.0, 100.0, allow_nan=False, allow_infinity=False),
        ),
        min_size=2,
        max_size=30,
    ),
    tolerance=st.floats(0.0, 20.0, allow_nan=False, allow_infinity=False),
)
def test_open_result_is_ordered_source_subsequence_with_bounded_residual(
    coordinates: list[tuple[float, float]],
    tolerance: float,
) -> None:
    source = Curve(tuple(Point2D(x, y) for x, y in coordinates), closed=False)

    result = simplify_curve_douglas_peucker(source, tolerance)

    assert result.curve.points == tuple(source.points[index] for index in result.retained_indices)
    assert result.retained_indices[0] == 0
    assert result.retained_indices[-1] == source.sample_count - 1
    assert result.curve.closed is False
    assert result.metrics.maximum_segment_deviation <= tolerance + 1e-10


@settings(max_examples=40, deadline=None)
@given(
    coordinates=st.lists(
        st.tuples(
            st.floats(-20.0, 20.0, allow_nan=False, allow_infinity=False),
            st.floats(-20.0, 20.0, allow_nan=False, allow_infinity=False),
        ),
        min_size=4,
        max_size=24,
        unique=True,
    ),
    tolerance=st.floats(0.0, 5.0, allow_nan=False, allow_infinity=False),
)
def test_closed_result_preserves_start_cyclic_order_and_topology(
    coordinates: list[tuple[float, float]],
    tolerance: float,
) -> None:
    source = Curve(tuple(Point2D(x, y) for x, y in coordinates), closed=True)

    result = simplify_curve_douglas_peucker(source, tolerance)

    assert result.retained_indices == tuple(sorted(result.retained_indices))
    assert result.retained_indices[0] == 0
    assert len(result.retained_indices) >= 3
    assert result.curve.closed
    assert result.curve.points[-1] != result.curve.points[0]
    assert result.metrics.maximum_segment_deviation <= tolerance + 1e-10
