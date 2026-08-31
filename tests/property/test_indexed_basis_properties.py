import pytest
from hypothesis import given
from hypothesis import strategies as st

from fourier_sketch.domain import BasisKind
from fourier_sketch.math import indexed_basis_analyze, indexed_synthesize


@given(
    st.sampled_from((BasisKind.DCT_II, BasisKind.WALSH_HADAMARD)),
    st.lists(
        st.complex_numbers(allow_nan=False, allow_infinity=False, max_magnitude=100),
        min_size=1,
        max_size=32,
    ),
)
def test_power_of_two_indexed_round_trip(
    basis: BasisKind, values: list[complex]
) -> None:
    size = 1 << (len(values).bit_length() - 1)
    values = values[:size] or [0j]
    assert indexed_synthesize(indexed_basis_analyze(values, basis)) == pytest.approx(
        values, abs=1e-10
    )
