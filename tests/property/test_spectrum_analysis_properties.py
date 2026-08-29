"""Measured K-sweep invariants."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from fourier_sketch.math import analyze_spectrum, fft_dft

pytestmark = pytest.mark.property


@given(
    st.lists(
        st.complex_numbers(allow_nan=False, allow_infinity=False, max_magnitude=100),
        min_size=2,
        max_size=32,
    )
)
def test_energy_is_monotone_and_full_reconstruction_is_exact(samples: list[complex]) -> None:
    source = tuple(samples)
    spectrum = fft_dft(source)
    ks = tuple(sorted({1, max(1, len(source) // 2), len(source)}))

    result = analyze_spectrum(spectrum, source, ks)

    energies = [point.retained_energy_ratio for point in result.sweep]
    assert energies == sorted(energies)
    assert energies[-1] == pytest.approx(1.0, abs=1e-12)
    assert result.sweep[-1].reconstruction_metrics.rmse == pytest.approx(0.0, abs=1e-10)
