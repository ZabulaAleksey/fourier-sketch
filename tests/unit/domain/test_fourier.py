"""Unit contracts for Fourier coefficient and spectrum values."""

from math import atan2, sqrt
from typing import cast

import pytest

from fourier_sketch.domain import (
    DomainValidationError,
    FourierCoefficient,
    FourierNormalization,
    FourierSpectrum,
    FrequencyConvention,
)

pytestmark = pytest.mark.unit


def test_coefficient_exposes_derived_components() -> None:
    coefficient = FourierCoefficient(frequency=-2, value=3.0 + 4.0j)

    assert coefficient.real == 3.0
    assert coefficient.imaginary == 4.0
    assert coefficient.amplitude == 5.0
    assert coefficient.phase == atan2(4.0, 3.0)


def test_zero_coefficient_has_stable_zero_phase() -> None:
    coefficient = FourierCoefficient(frequency=0, value=0.0j)

    assert coefficient.amplitude == 0.0
    assert coefficient.phase == 0.0


@pytest.mark.parametrize("value", [complex(float("nan"), 0), complex(0, float("inf"))])
def test_coefficient_rejects_non_finite_values(value: complex) -> None:
    with pytest.raises(DomainValidationError, match="finite"):
        FourierCoefficient(frequency=0, value=value)


def test_coefficient_rejects_boolean_frequency() -> None:
    invalid_frequency = cast(int, True)

    with pytest.raises(DomainValidationError, match="integer"):
        FourierCoefficient(frequency=invalid_frequency, value=1.0j)


def test_complete_spectrum_preserves_contract_and_metadata() -> None:
    coefficients = (
        FourierCoefficient(frequency=0, value=1.0 + 0.0j),
        FourierCoefficient(frequency=-1, value=0.0 + 1.0j),
    )
    spectrum = FourierSpectrum(
        coefficients=coefficients,
        sample_count=2,
        source_metadata=(("fixture", "two-sample"),),
    )

    assert spectrum.coefficients == coefficients
    assert spectrum.sample_count == 2
    assert spectrum.normalization is FourierNormalization.FORWARD_1_OVER_N
    assert spectrum.frequency_convention is FrequencyConvention.SIGNED
    assert spectrum.source_metadata == (("fixture", "two-sample"),)
    assert sum(item.amplitude**2 for item in spectrum.coefficients) == 2.0
    assert sqrt(sum(item.amplitude**2 for item in spectrum.coefficients)) == sqrt(2.0)


def test_spectrum_rejects_count_and_frequency_inconsistency() -> None:
    coefficient = FourierCoefficient(frequency=0, value=1.0 + 0.0j)

    with pytest.raises(DomainValidationError, match="sample_count coefficients"):
        FourierSpectrum(coefficients=(coefficient,), sample_count=2)

    duplicate = FourierCoefficient(frequency=0, value=2.0 + 0.0j)
    with pytest.raises(DomainValidationError, match="unique"):
        FourierSpectrum(coefficients=(coefficient, duplicate), sample_count=2)

    invalid_bins = (
        FourierCoefficient(frequency=100, value=1.0 + 0.0j),
        FourierCoefficient(frequency=101, value=2.0 + 0.0j),
    )
    with pytest.raises(DomainValidationError, match="canonical frequency set"):
        FourierSpectrum(coefficients=invalid_bins, sample_count=2)


def test_spectrum_rejects_non_positive_count_and_malformed_collections() -> None:
    invalid_coefficients = cast(tuple[FourierCoefficient, ...], None)
    coefficient = FourierCoefficient(frequency=0, value=1.0 + 0.0j)
    invalid_metadata = cast(tuple[tuple[str, str], ...], None)

    with pytest.raises(DomainValidationError, match="positive"):
        FourierSpectrum(coefficients=(), sample_count=0)
    with pytest.raises(DomainValidationError, match="coefficients"):
        FourierSpectrum(coefficients=invalid_coefficients, sample_count=1)
    with pytest.raises(DomainValidationError, match="source_metadata"):
        FourierSpectrum(
            coefficients=(coefficient,),
            sample_count=1,
            source_metadata=invalid_metadata,
        )


def test_spectrum_rejects_invalid_contract_enums() -> None:
    coefficient = FourierCoefficient(frequency=0, value=1.0 + 0.0j)
    invalid_normalization = cast(FourierNormalization, "other")
    invalid_frequency_convention = cast(FrequencyConvention, "unsigned")

    with pytest.raises(DomainValidationError, match="normalization"):
        FourierSpectrum(
            coefficients=(coefficient,),
            sample_count=1,
            normalization=invalid_normalization,
        )
    with pytest.raises(DomainValidationError, match="frequency_convention"):
        FourierSpectrum(
            coefficients=(coefficient,),
            sample_count=1,
            frequency_convention=invalid_frequency_convention,
        )


def test_spectrum_rejects_invalid_metadata() -> None:
    coefficient = FourierCoefficient(frequency=0, value=1.0 + 0.0j)

    with pytest.raises(DomainValidationError, match="unique"):
        FourierSpectrum(
            coefficients=(coefficient,),
            sample_count=1,
            source_metadata=(("fixture", "a"), ("fixture", "b")),
        )
    with pytest.raises(DomainValidationError, match="non-empty"):
        FourierSpectrum(
            coefficients=(coefficient,),
            sample_count=1,
            source_metadata=(("", "value"),),
        )

    malformed_entry = cast(tuple[str, str], ("key", "value", "extra"))
    with pytest.raises(DomainValidationError, match="pairs"):
        FourierSpectrum(
            coefficients=(coefficient,),
            sample_count=1,
            source_metadata=(malformed_entry,),
        )
