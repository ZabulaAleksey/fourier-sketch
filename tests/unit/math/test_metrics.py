"""Unit contracts for reconstruction and retained-energy metrics."""

from math import sqrt

import pytest

from fourier_sketch.domain import (
    CoefficientSelection,
    DomainValidationError,
    FourierCoefficient,
    FourierSpectrum,
    NormalizedErrorStatus,
    SpectrumOrdering,
)
from fourier_sketch.math import (
    reconstruction_metrics,
    retained_energy_ratio,
    select_first,
    select_frequencies,
)

pytestmark = pytest.mark.unit


def make_spectrum() -> FourierSpectrum:
    return FourierSpectrum(
        (
            FourierCoefficient(0, 3.0 + 0.0j),
            FourierCoefficient(1, 4.0 + 0.0j),
            FourierCoefficient(-1, 0.0j),
        ),
        sample_count=3,
    )


def test_reconstruction_metrics_match_documented_formulas() -> None:
    metrics = reconstruction_metrics((0.0j, 2.0 + 0.0j), (0.0j, 0.0j))

    assert metrics.mse == pytest.approx(2.0)
    assert metrics.rmse == pytest.approx(sqrt(2.0))
    assert metrics.max_error == pytest.approx(2.0)
    assert metrics.normalized_error == pytest.approx(sqrt(2.0))
    assert metrics.normalized_status is NormalizedErrorStatus.DEFINED


def test_zero_centered_reference_has_explicit_exact_or_undefined_state() -> None:
    exact = reconstruction_metrics((2.0j, 2.0j), (2.0j, 2.0j))
    different = reconstruction_metrics((2.0j, 2.0j), (1.0j, 2.0j))

    assert exact.normalized_error == 0.0
    assert exact.normalized_status is NormalizedErrorStatus.ZERO_REFERENCE_EXACT
    assert different.normalized_error is None
    assert different.normalized_status is NormalizedErrorStatus.UNDEFINED_ZERO_REFERENCE


def test_metrics_reject_misaligned_nonfinite_or_overflowing_values() -> None:
    with pytest.raises(DomainValidationError, match="equal length"):
        reconstruction_metrics((0.0j,), (0.0j, 1.0j))
    with pytest.raises(DomainValidationError, match="finite"):
        reconstruction_metrics((complex(float("nan"), 0.0),), (0.0j,))
    with pytest.raises(DomainValidationError, match="finite"):
        reconstruction_metrics((complex(1.7e308, 1.7e308),), (0.0j,))


def test_retained_energy_ratio_matches_squared_amplitudes() -> None:
    spectrum = make_spectrum()
    partial = select_frequencies(spectrum, (1,))
    full = select_first(spectrum, 3, SpectrumOrdering.SIGNED)

    assert retained_energy_ratio(partial, spectrum) == pytest.approx(16.0 / 25.0)
    assert retained_energy_ratio(full, spectrum) == 1.0


def test_zero_energy_ratio_is_one_for_full_and_zero_for_partial() -> None:
    spectrum = FourierSpectrum(
        (
            FourierCoefficient(0, 0.0j),
            FourierCoefficient(1, 0.0j),
            FourierCoefficient(-1, 0.0j),
        ),
        sample_count=3,
    )

    assert retained_energy_ratio(
        select_first(spectrum, 3, SpectrumOrdering.SIGNED), spectrum
    ) == 1.0
    assert retained_energy_ratio(select_frequencies(spectrum, (0,)), spectrum) == 0.0


def test_retained_energy_rejects_selection_from_different_spectrum() -> None:
    spectrum = make_spectrum()
    other = FourierSpectrum(
        (
            FourierCoefficient(0, 5.0 + 0.0j),
            FourierCoefficient(1, 4.0 + 0.0j),
            FourierCoefficient(-1, 0.0j),
        ),
        sample_count=3,
    )

    with pytest.raises(DomainValidationError, match="belong"):
        retained_energy_ratio(select_frequencies(other, (0,)), spectrum)


def test_retained_energy_uses_documented_coefficient_value_semantics() -> None:
    spectrum = make_spectrum()
    equivalent_selection = CoefficientSelection(
        (FourierCoefficient(0, 3.0 + 0.0j),),
        sample_count=3,
        ordering=SpectrumOrdering.EXPLICIT,
    )

    assert retained_energy_ratio(equivalent_selection, spectrum) == pytest.approx(9.0 / 25.0)


def test_full_retained_energy_still_rejects_unrepresentable_total() -> None:
    spectrum = FourierSpectrum(
        (FourierCoefficient(0, 1e308 + 0.0j),),
        sample_count=1,
    )
    full = select_first(spectrum, 1, SpectrumOrdering.SIGNED)

    with pytest.raises(DomainValidationError, match="finite"):
        retained_energy_ratio(full, spectrum)
