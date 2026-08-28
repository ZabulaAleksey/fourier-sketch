"""Coefficient selection from complete canonical Fourier spectra."""

from collections.abc import Sequence

from fourier_sketch.domain import (
    CoefficientSelection,
    DomainValidationError,
    FourierSpectrum,
    SpectrumOrdering,
)

from .spectrum import ordered_coefficients


def select_first(
    spectrum: FourierSpectrum,
    count: int,
    ordering: SpectrumOrdering,
) -> CoefficientSelection:
    """Select the first ``count`` coefficients from a deterministic complete view."""
    _require_spectrum(spectrum)
    if isinstance(count, bool) or not isinstance(count, int):
        raise DomainValidationError("count must be an integer")
    if count < 1 or count > spectrum.sample_count:
        raise DomainValidationError("count must be between 1 and sample_count")
    if ordering is SpectrumOrdering.EXPLICIT:
        raise DomainValidationError("explicit selection requires select_frequencies")

    view = ordered_coefficients(spectrum, ordering)
    return CoefficientSelection(view[:count], spectrum.sample_count, ordering)


def select_frequencies(
    spectrum: FourierSpectrum,
    frequencies: Sequence[int],
) -> CoefficientSelection:
    """Select an explicit unique subset while preserving caller order."""
    _require_spectrum(spectrum)
    try:
        requested = tuple(frequencies)
    except TypeError as error:
        raise DomainValidationError("frequencies must be an iterable collection") from error
    if not requested:
        raise DomainValidationError("frequencies must contain at least one value")
    if any(isinstance(value, bool) or not isinstance(value, int) for value in requested):
        raise DomainValidationError("frequencies must contain integers")
    if len(requested) != len(set(requested)):
        raise DomainValidationError("frequencies must be unique")

    by_frequency = {
        coefficient.frequency: coefficient for coefficient in spectrum.coefficients
    }
    if not set(requested).issubset(by_frequency):
        raise DomainValidationError("frequencies contain an unknown spectrum bin")
    return CoefficientSelection(
        tuple(by_frequency[frequency] for frequency in requested),
        spectrum.sample_count,
        SpectrumOrdering.EXPLICIT,
    )


def _require_spectrum(spectrum: FourierSpectrum) -> None:
    if not isinstance(spectrum, FourierSpectrum):
        raise DomainValidationError("spectrum must be a FourierSpectrum")
