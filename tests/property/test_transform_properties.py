"""Property contracts for Fourier transform parity and algebraic behavior."""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from fourier_sketch.math import fft_dft, idft, reference_dft

pytestmark = pytest.mark.property

ABS_TOL = 2e-10
REL_TOL = 2e-10  # N<=12 and |component|<=100 keep round-off tightly bounded.

finite_component = st.floats(
    min_value=-100.0,
    max_value=100.0,
    allow_nan=False,
    allow_infinity=False,
    width=64,
)
complex_value = st.builds(complex, finite_component, finite_component)
sample_sequences = st.lists(complex_value, min_size=1, max_size=12).map(tuple)


@settings(max_examples=60, deadline=None)
@given(sample_sequences)
def test_reference_and_numpy_fft_are_equivalent(samples: tuple[complex, ...]) -> None:
    reference = reference_dft(samples)
    optimized = fft_dft(samples)

    assert tuple(item.frequency for item in optimized.coefficients) == tuple(
        item.frequency for item in reference.coefficients
    )
    assert tuple(item.value for item in optimized.coefficients) == pytest.approx(
        tuple(item.value for item in reference.coefficients),
        abs=ABS_TOL,
        rel=REL_TOL,
    )


@settings(max_examples=60, deadline=None)
@given(sample_sequences)
def test_idft_round_trip_recovers_finite_samples(samples: tuple[complex, ...]) -> None:
    assert idft(fft_dft(samples)) == pytest.approx(samples, abs=ABS_TOL, rel=REL_TOL)


@settings(max_examples=40, deadline=None)
@given(sample_sequences, complex_value)
def test_translation_changes_only_dc(
    samples: tuple[complex, ...],
    offset: complex,
) -> None:
    base = {item.frequency: item.value for item in reference_dft(samples).coefficients}
    shifted = {
        item.frequency: item.value
        for item in reference_dft(tuple(value + offset for value in samples)).coefficients
    }

    assert shifted[0] == pytest.approx(base[0] + offset, abs=ABS_TOL, rel=REL_TOL)
    for frequency in base.keys() - {0}:
        assert shifted[frequency] == pytest.approx(
            base[frequency], abs=ABS_TOL, rel=REL_TOL
        )


@settings(max_examples=40, deadline=None)
@given(sample_sequences, complex_value)
def test_complex_scaling_scales_every_coefficient(
    samples: tuple[complex, ...],
    scale: complex,
) -> None:
    base = reference_dft(samples)
    scaled = reference_dft(tuple(value * scale for value in samples))

    assert tuple(item.value for item in scaled.coefficients) == pytest.approx(
        tuple(item.value * scale for item in base.coefficients),
        abs=ABS_TOL,
        rel=REL_TOL,
    )
