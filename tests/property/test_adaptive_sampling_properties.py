from hypothesis import given
from hypothesis import strategies as st

from fourier_sketch.domain import Curve, Point2D
from fourier_sketch.math import resample_curve_adaptive


@given(
    st.lists(
        st.tuples(
            st.floats(-10, 10, allow_nan=False, allow_infinity=False),
            st.floats(-10, 10, allow_nan=False, allow_infinity=False),
        ),
        min_size=2,
        max_size=12,
    )
)
def test_adaptive_sampling_is_deterministic_and_bounded(
    raw: list[tuple[float, float]],
) -> None:
    points = tuple(
        Point2D(float(index), float(index) + float(y) * 0.01) for index, (_, y) in enumerate(raw)
    )
    first = resample_curve_adaptive(Curve(points), 9, curvature_weight=10)
    second = resample_curve_adaptive(Curve(points), 9, curvature_weight=10)
    assert first.curve == second.curve
    assert len(first.curve.points) == 9
