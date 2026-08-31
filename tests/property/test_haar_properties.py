import pytest
from hypothesis import given
from hypothesis import strategies as st

from fourier_sketch.math import haar_analyze, haar_synthesize


@given(
    st.lists(
        st.complex_numbers(
            allow_nan=False,
            allow_infinity=False,
            max_magnitude=100,
        ),
        min_size=1,
        max_size=32,
    )
)
def test_power_of_two_complex_inputs_round_trip(values: list[complex]) -> None:
    size = 1 << (len(values).bit_length() - 1)
    if size != len(values):
        values = values[:size]
    if not values:
        values = [0j]
    decomposition = haar_analyze(values)
    assert haar_synthesize(decomposition) == pytest.approx(values, abs=1e-10)
    sample_energy = sum(abs(value) ** 2 for value in values)
    coefficient_energy = sum(abs(term.value) ** 2 for term in decomposition.terms)
    assert coefficient_energy == pytest.approx(sample_energy, rel=1e-12, abs=1e-9)
