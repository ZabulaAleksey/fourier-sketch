"""Bounded NumPy inverse-grid adapter shared by complete and sparse spectra."""

from collections.abc import Sequence

import numpy as np

from fourier_sketch.domain import FourierCoefficient

from ._validation import finite_complex_value
from .errors import FourierBackendError


def inverse_grid(
    coefficients: Sequence[FourierCoefficient],
    *,
    output_count: int,
) -> tuple[complex, ...]:
    """Evaluate Fourier coefficients on a discrete grid through a bounded inverse FFT."""

    try:
        bins = np.zeros(output_count, dtype=np.complex128)
        with np.errstate(over="ignore", invalid="ignore"):
            for coefficient in coefficients:
                bins[coefficient.frequency % output_count] += coefficient.value
            reconstructed = np.fft.ifft(bins) * output_count
    except Exception as error:
        raise FourierBackendError("NumPy inverse FFT backend failed") from error

    return tuple(
        finite_complex_value(complex(value), field_name=f"reconstruction[{index}]")
        for index, value in enumerate(reconstructed)
    )
