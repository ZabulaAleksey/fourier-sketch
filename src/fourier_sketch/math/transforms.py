"""Reference and NumPy-backed one-dimensional Fourier transforms."""

from cmath import exp
from collections.abc import Sequence
from math import pi

import numpy as np

from fourier_sketch.domain import (
    DomainValidationError,
    FourierCoefficient,
    FourierSpectrum,
)

from ._validation import finite_complex_samples, finite_complex_value
from .errors import FourierBackendError
from .frequencies import signed_frequencies

MAX_REFERENCE_SAMPLES = 2048
MAX_FFT_SAMPLES = 262_144


def reference_dft(samples: Sequence[complex]) -> FourierSpectrum:
    """Compute the canonical O(N²) forward transform as a bounded correctness oracle."""
    values = finite_complex_samples(samples, max_count=MAX_REFERENCE_SAMPLES)
    sample_count = len(values)

    coefficients = tuple(
        FourierCoefficient(
            frequency=frequency,
            value=sum(
                value * exp(-2j * pi * frequency * index / sample_count)
                for index, value in enumerate(values)
            )
            / sample_count,
        )
        for frequency in signed_frequencies(sample_count)
    )
    return FourierSpectrum(
        coefficients=coefficients,
        sample_count=sample_count,
        source_metadata=(("backend", "reference"),),
    )


def fft_dft(samples: Sequence[complex]) -> FourierSpectrum:
    """Compute the canonical forward transform with the explicitly selected NumPy backend."""
    values = finite_complex_samples(samples, max_count=MAX_FFT_SAMPLES)
    sample_count = len(values)
    try:
        transformed = np.fft.fft(np.asarray(values, dtype=np.complex128)) / sample_count
    except Exception as error:
        raise FourierBackendError("NumPy FFT backend failed") from error

    coefficients = tuple(
        FourierCoefficient(frequency, complex(value))
        for frequency, value in zip(
            signed_frequencies(sample_count), transformed, strict=True
        )
    )
    return FourierSpectrum(
        coefficients=coefficients,
        sample_count=sample_count,
        source_metadata=(("backend", "numpy_fft"),),
    )


def idft(spectrum: FourierSpectrum) -> tuple[complex, ...]:
    """Reconstruct the sample grid from a complete canonical spectrum."""
    if not isinstance(spectrum, FourierSpectrum):
        raise DomainValidationError("spectrum must be a FourierSpectrum")
    sample_count = spectrum.sample_count
    reconstructed = tuple(
        sum(
            coefficient.value
            * exp(2j * pi * coefficient.frequency * index / sample_count)
            for coefficient in spectrum.coefficients
        )
        for index in range(sample_count)
    )
    return tuple(
        finite_complex_value(value, field_name=f"reconstruction[{index}]")
        for index, value in enumerate(reconstructed)
    )
