"""Property contracts for the FS-007 index-resampling baseline."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from fourier_sketch.domain import Curve, Point2D
from fourier_sketch.math import cleanup_consecutive_duplicates, resample_curve_by_index

pytestmark = pytest.mark.property


@given(
    coordinates=st.lists(
        st.tuples(
            st.floats(min_value=-100.0, max_value=100.0, allow_nan=False, allow_infinity=False),
            st.floats(min_value=-100.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        ),
        min_size=2,
        max_size=30,
    ),
    sample_count=st.integers(min_value=2, max_value=128),
)
def test_open_index_resampling_preserves_cleaned_endpoints_and_count(
    coordinates: list[tuple[float, float]],
    sample_count: int,
) -> None:
    points = tuple(Point2D(x, y) for x, y in coordinates)
    cleaned = cleanup_consecutive_duplicates(points)
    curve = Curve(points, closed=False)

    result = resample_curve_by_index(curve, sample_count)

    if len(cleaned) == 1:
        assert result.points == (cleaned[0],)
    else:
        assert result.sample_count == sample_count
        assert result.start == cleaned[0]
        assert result.end == cleaned[-1]
    assert result.closed is False
