"""Unit contracts for complete-spectrum views and energy."""

from typing import cast

import pytest

from fourier_sketch.domain import (
    DomainValidationError,
    FourierCoefficient,
    FourierSpectrum,
    SpectrumOrdering,
)
from fourier_sketch.math import ordered_coefficients, spectrum_energy

pytestmark = pytest.mark.unit


def make_spectrum() -> FourierSpectrum:
    return FourierSpectrum(
        coefficients=(
            FourierCoefficient(0, 1.0 + 0.0j),
            FourierCoefficient(1, 3.0 + 0.0j),
            FourierCoefficient(2, 2.0 + 0.0j),
            FourierCoefficient(-2, -2.0 + 0.0j),
            FourierCoefficient(-1, -3.0 + 0.0j),
        ),
        sample_count=5,
    )


@pytest.mark.parametrize(
    ("ordering", "expected"),
    [
        (SpectrumOrdering.SIGNED, (-2, -1, 0, 1, 2)),
        (SpectrumOrdering.ABSOLUTE_FREQUENCY, (0, -1, 1, -2, 2)),
        (SpectrumOrdering.AMPLITUDE_DESCENDING, (-1, 1, -2, 2, 0)),
        (SpectrumOrdering.INTERLEAVED, (0, 1, -1, 2, -2)),
    ],
)
def test_orderings_use_documented_deterministic_ties(
    ordering: SpectrumOrdering,
    expected: tuple[int, ...],
) -> None:
    ordered = ordered_coefficients(make_spectrum(), ordering)

    assert tuple(item.frequency for item in ordered) == expected


@pytest.mark.parametrize(
    ("sample_count", "expected"),
    [(4, (0, 1, -1, -2)), (2, (0, -1))],
)
def test_interleaved_ordering_places_even_nyquist_last(
    sample_count: int,
    expected: tuple[int, ...],
) -> None:
    coefficients = tuple(
        FourierCoefficient(frequency, complex(index))
        for index, frequency in enumerate(expected)
    )
    spectrum = FourierSpectrum(coefficients, sample_count=sample_count)

    ordered = ordered_coefficients(spectrum, SpectrumOrdering.INTERLEAVED)

    assert tuple(item.frequency for item in ordered) == expected


def test_explicit_ordering_preserves_complete_caller_order() -> None:
    spectrum = make_spectrum()
    frequencies = (2, -2, 1, -1, 0)

    ordered = ordered_coefficients(
        spectrum,
        SpectrumOrdering.EXPLICIT,
        explicit_frequencies=frequencies,
    )

    assert tuple(item.frequency for item in ordered) == frequencies
    assert set(ordered) == set(spectrum.coefficients)


@pytest.mark.parametrize(
    "frequencies",
    [None, (0, 1), (0, 1, 2, -2, -2), (0, 1, 2, -2, 99)],
)
def test_explicit_ordering_rejects_incomplete_duplicate_or_unknown_frequency(
    frequencies: tuple[int, ...] | None,
) -> None:
    with pytest.raises(DomainValidationError, match=r"explicit|every|unique|unknown"):
        ordered_coefficients(
            make_spectrum(),
            SpectrumOrdering.EXPLICIT,
            explicit_frequencies=frequencies,
        )


def test_non_explicit_ordering_rejects_extra_explicit_argument() -> None:
    with pytest.raises(DomainValidationError, match="only for explicit"):
        ordered_coefficients(
            make_spectrum(),
            SpectrumOrdering.SIGNED,
            explicit_frequencies=(0, 1, 2, -2, -1),
        )


def test_unknown_ordering_is_a_typed_error() -> None:
    invalid = cast(SpectrumOrdering, "unknown")

    with pytest.raises(DomainValidationError, match="SpectrumOrdering"):
        ordered_coefficients(make_spectrum(), invalid)


def test_spectrum_energy_is_squared_amplitude_sum() -> None:
    assert spectrum_energy(make_spectrum()) == 27.0
    zero = FourierSpectrum((FourierCoefficient(0, 0.0j),), sample_count=1)
    assert spectrum_energy(zero) == 0.0


def test_spectrum_energy_rejects_overflow() -> None:
    spectrum = FourierSpectrum((FourierCoefficient(0, 1e308 + 0.0j),), sample_count=1)

    with pytest.raises(DomainValidationError, match="finite"):
        spectrum_energy(spectrum)


def test_amplitude_ordering_rejects_overflow_safe_magnitude() -> None:
    spectrum = FourierSpectrum(
        (FourierCoefficient(0, complex(1.7e308, 1.7e308)),),
        sample_count=1,
    )

    with pytest.raises(DomainValidationError, match="amplitude must be finite"):
        ordered_coefficients(spectrum, SpectrumOrdering.AMPLITUDE_DESCENDING)
