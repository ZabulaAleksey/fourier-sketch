"""Public numerical API for Fourier Sketch."""

from .conversion import (
    complex_samples_to_curve,
    complex_to_point,
    curve_to_complex_samples,
    point_to_complex,
)
from .epicycles import build_epicycle_chain, rotating_value
from .errors import FourierBackendError
from .fft2_image import (
    MAX_FFT2_PIXELS,
    FFT2Image,
    FFT2MaskPolicy,
    FFT2Raster,
    FFT2Spectrum,
    fft2_image,
    ifft2_image,
)
from .frequencies import signed_frequencies, signed_frequency
from .metrics import reconstruction_metrics, retained_energy_ratio
from .piecewise_sampling import (
    MAX_PIECEWISE_SAMPLES,
    PiecewiseAllocation,
    PiecewiseBoundary,
    PiecewiseSampled,
    sample_piecewise_curve,
)
from .reconstruction import (
    MAX_RECONSTRUCTION_SAMPLES,
    MAX_RECONSTRUCTION_TERMS,
    reconstruct_at,
    reconstruct_samples,
)
from .resampling import (
    MAX_RESAMPLED_POINTS,
    CurveSpacingMetrics,
    ResamplingMethod,
    cleanup_consecutive_duplicates,
    curve_spacing_metrics,
    resample_curve_by_arc_length,
    resample_curve_by_index,
)
from .selection import select_first, select_frequencies
from .spectrum import ordered_coefficients, spectrum_energy
from .spectrum_analysis import (
    KSweepPoint,
    SpectrumAnalysis,
    SpectrumAnalysisStatus,
    SpectrumPoint,
    analyze_spectrum,
)
from .transforms import MAX_FFT_SAMPLES, MAX_REFERENCE_SAMPLES, fft_dft, idft, reference_dft

__all__ = [
    "MAX_FFT2_PIXELS",
    "MAX_FFT_SAMPLES",
    "MAX_PIECEWISE_SAMPLES",
    "MAX_RECONSTRUCTION_SAMPLES",
    "MAX_RECONSTRUCTION_TERMS",
    "MAX_REFERENCE_SAMPLES",
    "MAX_RESAMPLED_POINTS",
    "CurveSpacingMetrics",
    "FFT2Image",
    "FFT2MaskPolicy",
    "FFT2Raster",
    "FFT2Spectrum",
    "FourierBackendError",
    "KSweepPoint",
    "PiecewiseAllocation",
    "PiecewiseBoundary",
    "PiecewiseSampled",
    "ResamplingMethod",
    "SpectrumAnalysis",
    "SpectrumAnalysisStatus",
    "SpectrumPoint",
    "analyze_spectrum",
    "build_epicycle_chain",
    "cleanup_consecutive_duplicates",
    "complex_samples_to_curve",
    "complex_to_point",
    "curve_spacing_metrics",
    "curve_to_complex_samples",
    "fft2_image",
    "fft_dft",
    "idft",
    "ifft2_image",
    "ordered_coefficients",
    "point_to_complex",
    "reconstruct_at",
    "reconstruct_samples",
    "reconstruction_metrics",
    "reference_dft",
    "resample_curve_by_arc_length",
    "resample_curve_by_index",
    "retained_energy_ratio",
    "rotating_value",
    "sample_piecewise_curve",
    "select_first",
    "select_frequencies",
    "signed_frequencies",
    "signed_frequency",
    "spectrum_energy",
]
