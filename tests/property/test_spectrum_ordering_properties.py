"""Property contracts for complete-spectrum ordering views."""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from fourier_sketch.domain import SpectrumOrdering
from fourier_sketch.math import fft_dft, ordered_coefficients

pytestmark = pytest.mark.property

finite_component = st.floats(
    min_value=-50.0,
    max_value=50.0,
    allow_nan=False,
    allow_infinity=False,
)
complex_value = st.builds(complex, finite_component, finite_component)
sample_sequences = st.lists(complex_value, min_size=1, max_size=24).map(tuple)


@settings(max_examples=50, deadline=None)
@given(sample_sequences)
def test_each_ordering_is_a_deterministic_permutation(samples: tuple[complex, ...]) -> None:
    spectrum = fft_dft(samples)
    expected = set(spectrum.coefficients)

    for ordering in (
        SpectrumOrdering.SIGNED,
        SpectrumOrdering.ABSOLUTE_FREQUENCY,
        SpectrumOrdering.AMPLITUDE_DESCENDING,
        SpectrumOrdering.INTERLEAVED,
    ):
        first = ordered_coefficients(spectrum, ordering)
        second = ordered_coefficients(spectrum, ordering)
        assert first == second
        assert len(first) == spectrum.sample_count
        assert set(first) == expected

    explicit = ordered_coefficients(
        spectrum,
        SpectrumOrdering.EXPLICIT,
        explicit_frequencies=tuple(
            coefficient.frequency for coefficient in reversed(spectrum.coefficients)
        ),
    )
    assert set(explicit) == expected
