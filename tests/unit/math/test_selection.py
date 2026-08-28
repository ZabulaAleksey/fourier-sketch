"""Unit contracts for coefficient selection and reconstruction."""

from cmath import exp
from math import pi
from typing import cast

import pytest

from fourier_sketch.domain import (
    CoefficientSelection,
    DomainValidationError,
    FourierCoefficient,
    FourierSpectrum,
    SpectrumOrdering,
)
from fourier_sketch.math import (
    MAX_RECONSTRUCTION_SAMPLES,
    MAX_RECONSTRUCTION_TERMS,
    fft_dft,
    reconstruct_at,
    reconstruct_samples,
    select_first,
    select_frequencies,
)

pytestmark = pytest.mark.unit

ABS_TOL = 1e-12


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


def test_select_first_uses_requested_deterministic_view() -> None:
    selection = select_first(
        make_spectrum(),
        3,
        SpectrumOrdering.AMPLITUDE_DESCENDING,
    )

    assert selection.frequencies == (-1, 1, -2)
    assert selection.coefficient_count == 3
    assert not selection.is_full
    assert selection.ordering is SpectrumOrdering.AMPLITUDE_DESCENDING


def test_select_frequencies_preserves_unique_caller_subset_order() -> None:
    selection = select_frequencies(make_spectrum(), (2, -1, 0))

    assert selection.frequencies == (2, -1, 0)
    assert selection.ordering is SpectrumOrdering.EXPLICIT


@pytest.mark.parametrize("count", [0, 6, -1, 1.5, True])
def test_select_first_rejects_invalid_count(count: object) -> None:
    with pytest.raises(DomainValidationError, match="count"):
        select_first(
            make_spectrum(),
            cast(int, count),
            SpectrumOrdering.SIGNED,
        )


def test_select_first_requires_non_explicit_ordering() -> None:
    with pytest.raises(DomainValidationError, match="select_frequencies"):
        select_first(make_spectrum(), 1, SpectrumOrdering.EXPLICIT)


@pytest.mark.parametrize(
    "frequencies",
    [(), (0, 0), (0, 99), (0, 1.5), (True,)],
)
def test_explicit_selection_rejects_empty_duplicate_unknown_or_non_integer(
    frequencies: tuple[object, ...],
) -> None:
    with pytest.raises(DomainValidationError, match="frequencies"):
        select_frequencies(make_spectrum(), cast(tuple[int, ...], frequencies))


def test_selection_domain_rejects_noncanonical_partial_spectrum() -> None:
    with pytest.raises(DomainValidationError, match="canonical"):
        CoefficientSelection(
            (FourierCoefficient(99, 1.0j),),
            sample_count=5,
            ordering=SpectrumOrdering.EXPLICIT,
        )


def test_reconstruct_at_evaluates_continuous_periodic_sum() -> None:
    spectrum = FourierSpectrum((FourierCoefficient(0, 2.0 - 1.0j),), sample_count=1)
    stationary = select_first(spectrum, 1, SpectrumOrdering.SIGNED)
    assert reconstruct_at(stationary, -3.75) == pytest.approx(2.0 - 1.0j, abs=ABS_TOL)

    rotating = CoefficientSelection(
        (FourierCoefficient(1, 1.0 + 0.0j),),
        sample_count=3,
        ordering=SpectrumOrdering.EXPLICIT,
    )
    assert reconstruct_at(rotating, 0.25) == pytest.approx(1.0j, abs=ABS_TOL)
    assert reconstruct_at(rotating, 0.25 + 4.0) == pytest.approx(1.0j, abs=ABS_TOL)


def test_explicit_subset_reconstruction_uses_preserved_caller_set_and_order() -> None:
    spectrum = make_spectrum()
    selection = select_frequencies(spectrum, (2, -1, 0))
    time = 0.375
    expected = sum(
        coefficient.value
        * exp(2j * pi * coefficient.frequency * time)
        for coefficient in selection.coefficients
    )

    assert selection.frequencies == (2, -1, 0)
    assert reconstruct_at(selection, time) == pytest.approx(expected, abs=ABS_TOL)
    assert reconstruct_samples(selection, sample_count=8) == pytest.approx(
        tuple(reconstruct_at(selection, index / 8) for index in range(8)),
        abs=ABS_TOL,
    )


def test_reconstruct_samples_uses_requested_output_grid() -> None:
    selection = CoefficientSelection(
        (FourierCoefficient(1, 1.0 + 0.0j),),
        sample_count=4,
        ordering=SpectrumOrdering.EXPLICIT,
    )

    assert reconstruct_samples(selection) == pytest.approx(
        (1.0 + 0.0j, 1.0j, -1.0 + 0.0j, -1.0j),
        abs=ABS_TOL,
    )
    assert reconstruct_samples(selection, sample_count=2) == pytest.approx(
        (1.0 + 0.0j, -1.0 + 0.0j),
        abs=ABS_TOL,
    )


def test_reconstruct_samples_rejects_pre_allocation_and_work_budget() -> None:
    selection = select_first(fft_dft((0.0j,) * 65), 65, SpectrumOrdering.SIGNED)

    with pytest.raises(DomainValidationError, match=str(MAX_RECONSTRUCTION_SAMPLES)):
        reconstruct_samples(selection, sample_count=MAX_RECONSTRUCTION_SAMPLES + 1)
    with pytest.raises(DomainValidationError, match=str(MAX_RECONSTRUCTION_TERMS)):
        reconstruct_samples(
            selection,
            sample_count=MAX_RECONSTRUCTION_TERMS // selection.coefficient_count + 1,
        )


@pytest.mark.parametrize("time", [float("nan"), float("inf"), True, "0"])
def test_reconstruct_at_rejects_invalid_time(time: object) -> None:
    selection = select_first(make_spectrum(), 1, SpectrumOrdering.SIGNED)

    with pytest.raises(DomainValidationError, match="time"):
        reconstruct_at(selection, cast(float, time))


def test_reconstruction_formula_documents_positive_rotation() -> None:
    selection = CoefficientSelection(
        (FourierCoefficient(2, 2.0 + 0.0j),),
        sample_count=5,
        ordering=SpectrumOrdering.EXPLICIT,
    )

    assert reconstruct_at(selection, 0.125) == pytest.approx(
        2.0 * complex(0.0, 1.0),
        abs=ABS_TOL * pi,
    )
