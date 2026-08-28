"""Reconstruction-error and retained-energy metrics."""

from collections.abc import Sequence
from math import fsum, hypot, isfinite, sqrt

from fourier_sketch.domain import (
    CoefficientSelection,
    DomainValidationError,
    FourierSpectrum,
    NormalizedErrorStatus,
    ReconstructionMetrics,
)

from ._validation import finite_complex_samples
from .reconstruction import MAX_RECONSTRUCTION_SAMPLES
from .spectrum import spectrum_energy


def reconstruction_metrics(
    reference: Sequence[complex],
    reconstruction: Sequence[complex],
) -> ReconstructionMetrics:
    """Calculate documented errors for two aligned finite sequences."""
    expected = finite_complex_samples(reference, max_count=MAX_RECONSTRUCTION_SAMPLES)
    actual = finite_complex_samples(reconstruction, max_count=MAX_RECONSTRUCTION_SAMPLES)
    if len(expected) != len(actual):
        raise DomainValidationError("reference and reconstruction must have equal length")

    errors = tuple(left - right for left, right in zip(expected, actual, strict=True))
    error_magnitudes = tuple(_magnitude(value, field_name="error") for value in errors)
    error_squares = tuple(value * value for value in error_magnitudes)
    mse = _finite_sum(error_squares, field_name="mse numerator") / len(expected)
    if not isfinite(mse):
        raise DomainValidationError("mse must be finite")
    rmse = sqrt(mse)
    max_error = max(error_magnitudes)

    mean = _finite_complex_mean(expected)
    centered = tuple(value - mean for value in expected)
    reference_norm_squared = _finite_sum(
        tuple(
            _finite_square(
                _magnitude(value, field_name="centered reference"),
                field_name="reference norm",
            )
            for value in centered
        ),
        field_name="reference norm",
    )
    error_norm_squared = _finite_sum(error_squares, field_name="error norm")

    if reference_norm_squared == 0.0:
        if error_norm_squared == 0.0:
            normalized_error: float | None = 0.0
            status = NormalizedErrorStatus.ZERO_REFERENCE_EXACT
        else:
            normalized_error = None
            status = NormalizedErrorStatus.UNDEFINED_ZERO_REFERENCE
    else:
        normalized_error = sqrt(error_norm_squared / reference_norm_squared)
        if not isfinite(normalized_error):
            raise DomainValidationError("normalized_error must be finite")
        status = NormalizedErrorStatus.DEFINED

    return ReconstructionMetrics(
        mse=mse,
        rmse=rmse,
        max_error=max_error,
        normalized_error=normalized_error,
        normalized_status=status,
    )


def retained_energy_ratio(
    selection: CoefficientSelection,
    spectrum: FourierSpectrum,
) -> float:
    """Return selected squared-amplitude energy relative to its source spectrum."""
    if not isinstance(selection, CoefficientSelection):
        raise DomainValidationError("selection must be a CoefficientSelection")
    if not isinstance(spectrum, FourierSpectrum):
        raise DomainValidationError("spectrum must be a FourierSpectrum")
    if selection.sample_count != spectrum.sample_count:
        raise DomainValidationError("selection and spectrum sample_count must match")

    by_frequency = {
        coefficient.frequency: coefficient.value for coefficient in spectrum.coefficients
    }
    if any(
        by_frequency.get(coefficient.frequency) != coefficient.value
        for coefficient in selection.coefficients
    ):
        raise DomainValidationError("selection coefficients must belong to the spectrum")
    total = spectrum_energy(spectrum)
    if selection.is_full:
        return 1.0
    if total == 0.0:
        return 0.0
    selected = _finite_sum(
        tuple(
            _finite_square(coefficient.amplitude, field_name="selected energy")
            for coefficient in selection.coefficients
        ),
        field_name="selected energy",
    )
    ratio = selected / total
    if not isfinite(ratio):
        raise DomainValidationError("retained energy ratio must be finite")
    return ratio


def _magnitude(value: complex, *, field_name: str) -> float:
    magnitude = hypot(value.real, value.imag)
    if not isfinite(magnitude):
        raise DomainValidationError(f"{field_name} magnitude must be finite")
    return magnitude


def _finite_sum(values: tuple[float, ...], *, field_name: str) -> float:
    try:
        result = fsum(values)
    except OverflowError as error:
        raise DomainValidationError(f"{field_name} must be finite") from error
    if not isfinite(result):
        raise DomainValidationError(f"{field_name} must be finite")
    return result


def _finite_square(value: float, *, field_name: str) -> float:
    result = value * value
    if not isfinite(result):
        raise DomainValidationError(f"{field_name} must be finite")
    return result


def _finite_complex_mean(values: tuple[complex, ...]) -> complex:
    count = len(values)
    try:
        mean = complex(
            fsum(value.real for value in values) / count,
            fsum(value.imag for value in values) / count,
        )
    except OverflowError as error:
        raise DomainValidationError("reference mean must be finite") from error
    if not isfinite(mean.real) or not isfinite(mean.imag):
        raise DomainValidationError("reference mean must be finite")
    return mean
