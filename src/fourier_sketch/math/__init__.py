"""Public numerical API for Fourier Sketch."""

from .conversion import (
    complex_samples_to_curve,
    complex_to_point,
    curve_to_complex_samples,
    point_to_complex,
)
from .errors import FourierBackendError
from .frequencies import signed_frequencies, signed_frequency
from .metrics import reconstruction_metrics, retained_energy_ratio
from .reconstruction import (
    MAX_RECONSTRUCTION_SAMPLES,
    MAX_RECONSTRUCTION_TERMS,
    reconstruct_at,
    reconstruct_samples,
)
from .selection import select_first, select_frequencies
from .spectrum import ordered_coefficients, spectrum_energy
from .transforms import MAX_FFT_SAMPLES, MAX_REFERENCE_SAMPLES, fft_dft, idft, reference_dft

__all__ = [
    "MAX_FFT_SAMPLES",
    "MAX_RECONSTRUCTION_SAMPLES",
    "MAX_RECONSTRUCTION_TERMS",
    "MAX_REFERENCE_SAMPLES",
    "FourierBackendError",
    "complex_samples_to_curve",
    "complex_to_point",
    "curve_to_complex_samples",
    "fft_dft",
    "idft",
    "ordered_coefficients",
    "point_to_complex",
    "reconstruct_at",
    "reconstruct_samples",
    "reconstruction_metrics",
    "reference_dft",
    "retained_energy_ratio",
    "select_first",
    "select_frequencies",
    "signed_frequencies",
    "signed_frequency",
    "spectrum_energy",
]
