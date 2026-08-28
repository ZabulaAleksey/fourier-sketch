"""Integration contract for transform → spectrum ordering/energy analysis."""

from cmath import exp
from math import pi

import pytest

from fourier_sketch.domain import SpectrumOrdering
from fourier_sketch.math import fft_dft, ordered_coefficients, spectrum_energy

pytestmark = pytest.mark.integration


def test_circle_spectrum_has_expected_dominant_harmonic_and_metadata() -> None:
    sample_count = 32
    circle = tuple(exp(2j * pi * index / sample_count) for index in range(sample_count))
    spectrum = fft_dft(circle)

    by_amplitude = ordered_coefficients(spectrum, SpectrumOrdering.AMPLITUDE_DESCENDING)

    assert by_amplitude[0].frequency == 1
    assert by_amplitude[0].amplitude == pytest.approx(1.0, abs=1e-12)
    assert spectrum_energy(spectrum) == pytest.approx(1.0, abs=1e-12)
    assert spectrum.source_metadata == (("backend", "numpy_fft"),)
