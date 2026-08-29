"""Generated FFT2 round-trip properties."""

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from fourier_sketch.math import fft2_image

pytestmark = pytest.mark.property


@st.composite
def _arrays(draw: st.DrawFn) -> np.ndarray:
    height = draw(st.integers(1, 8))
    width = draw(st.integers(1, 8))
    values = draw(
        st.lists(
            st.floats(-100, 100, allow_nan=False, allow_infinity=False),
            min_size=height * width,
            max_size=height * width,
        )
    )
    return np.asarray(values).reshape(height, width)


@given(_arrays())
def test_real_finite_arrays_round_trip(values: np.ndarray) -> None:
    result = fft2_image(values)
    assert result.reconstruct() == pytest.approx(values, abs=1e-10)
    assert result.shifted_magnitude.shape == values.shape
    assert result.shifted_phase.shape == values.shape
