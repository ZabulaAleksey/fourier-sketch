"""Deterministic views and summaries for complete Fourier spectra."""

from collections.abc import Sequence
from math import isfinite

from fourier_sketch.domain import (
    DomainValidationError,
    FourierCoefficient,
    FourierSpectrum,
    SpectrumOrdering,
)


def spectrum_energy(spectrum: FourierSpectrum) -> float:
    """Return total squared-amplitude energy for a complete spectrum."""
    _require_spectrum(spectrum)
    energy = sum(
        coefficient.amplitude * coefficient.amplitude
        for coefficient in spectrum.coefficients
    )
    if not isfinite(energy):
        raise DomainValidationError("spectrum energy must be finite")
    return energy


def ordered_coefficients(
    spectrum: FourierSpectrum,
    ordering: SpectrumOrdering,
    *,
    explicit_frequencies: Sequence[int] | None = None,
) -> tuple[FourierCoefficient, ...]:
    """Return a deterministic coefficient view without mutating the spectrum."""
    _require_spectrum(spectrum)
    if not isinstance(ordering, SpectrumOrdering):
        raise DomainValidationError("ordering must be a SpectrumOrdering")

    coefficients = spectrum.coefficients
    if ordering is SpectrumOrdering.EXPLICIT:
        return _explicit_order(coefficients, explicit_frequencies)
    if explicit_frequencies is not None:
        raise DomainValidationError("explicit_frequencies are valid only for explicit ordering")

    if ordering is SpectrumOrdering.SIGNED:
        return tuple(sorted(coefficients, key=lambda item: item.frequency))
    if ordering is SpectrumOrdering.ABSOLUTE_FREQUENCY:
        return tuple(
            sorted(coefficients, key=lambda item: (abs(item.frequency), item.frequency))
        )
    if ordering is SpectrumOrdering.AMPLITUDE_DESCENDING:
        return tuple(
            sorted(
                coefficients,
                key=lambda item: (-item.amplitude, abs(item.frequency), item.frequency),
            )
        )
    return tuple(sorted(coefficients, key=lambda item: _interleaved_rank(item.frequency)))


def _explicit_order(
    coefficients: tuple[FourierCoefficient, ...],
    explicit_frequencies: Sequence[int] | None,
) -> tuple[FourierCoefficient, ...]:
    if explicit_frequencies is None:
        raise DomainValidationError("explicit ordering requires explicit_frequencies")
    try:
        frequencies = tuple(explicit_frequencies)
    except TypeError as error:
        raise DomainValidationError(
            "explicit_frequencies must be an iterable collection"
        ) from error
    if any(
        isinstance(frequency, bool) or not isinstance(frequency, int)
        for frequency in frequencies
    ):
        raise DomainValidationError("explicit frequencies must be integers")
    if len(frequencies) != len(coefficients):
        raise DomainValidationError("explicit ordering must contain every spectrum frequency")
    if len(frequencies) != len(set(frequencies)):
        raise DomainValidationError("explicit frequencies must be unique")

    by_frequency = {coefficient.frequency: coefficient for coefficient in coefficients}
    if set(frequencies) != set(by_frequency):
        raise DomainValidationError("explicit ordering contains unknown or missing frequencies")
    return tuple(by_frequency[frequency] for frequency in frequencies)


def _interleaved_rank(frequency: int) -> int:
    if frequency == 0:
        return 0
    if frequency > 0:
        return 2 * frequency - 1
    return 2 * abs(frequency)


def _require_spectrum(spectrum: FourierSpectrum) -> None:
    if not isinstance(spectrum, FourierSpectrum):
        raise DomainValidationError("spectrum must be a FourierSpectrum")
