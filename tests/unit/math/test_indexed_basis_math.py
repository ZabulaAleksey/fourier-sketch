from math import sqrt

import pytest

from fourier_sketch.domain import BasisKind, DomainValidationError
from fourier_sketch.math import (
    dct_ii_analyze,
    dct_ii_synthesize,
    indexed_basis_analyze,
    indexed_synthesize,
    indexed_term_contribution,
    select_indexed_terms,
    walsh_hadamard_analyze,
    walsh_hadamard_synthesize,
)


@pytest.mark.parametrize("basis", (BasisKind.DCT_II, BasisKind.WALSH_HADAMARD))
@pytest.mark.parametrize(
    "samples",
    ((1,), (1, 1, 1, 1), (1, 0, 0, 0), (1 + 2j, -0.5j, 2 - 1j, -3j)),
)
def test_indexed_full_round_trip(basis: BasisKind, samples: tuple[complex, ...]) -> None:
    decomposition = indexed_basis_analyze(samples, basis)
    assert indexed_synthesize(decomposition) == pytest.approx(samples, abs=1e-12)


def test_dct_dc_and_first_ac_coefficients_are_orthonormal() -> None:
    decomposition = dct_ii_analyze((1, 3))
    assert decomposition.terms[0].value == pytest.approx(4 / sqrt(2))
    assert decomposition.terms[1].value == pytest.approx(-2 / sqrt(2))


def test_named_synthesis_helpers_require_the_matching_basis() -> None:
    dct = dct_ii_analyze((1, 2, 3, 4))
    walsh = walsh_hadamard_analyze((1, 2, 3, 4))
    assert dct_ii_synthesize(dct) == pytest.approx((1, 2, 3, 4), abs=1e-12)
    assert walsh_hadamard_synthesize(walsh) == pytest.approx((1, 2, 3, 4), abs=1e-12)
    with pytest.raises(DomainValidationError):
        dct_ii_synthesize(walsh)
    with pytest.raises(DomainValidationError):
        walsh_hadamard_synthesize(dct)


def test_walsh_uses_natural_sylvester_order() -> None:
    decomposition = walsh_hadamard_analyze((1, 2, 3, 4))
    assert decomposition.coefficients == pytest.approx((5, -1, -2, 0))


def test_partial_reconstruction_equals_sum_of_selected_contributions() -> None:
    decomposition = dct_ii_analyze((1, 2, 3, 4))
    selection = select_indexed_terms(decomposition, 2)
    partial = indexed_synthesize(selection)
    contributions = tuple(indexed_term_contribution(term, 4) for term in selection.terms)
    summed = tuple(sum(values[index] for values in contributions) for index in range(4))
    assert partial == pytest.approx(summed, abs=1e-12)


def test_indexed_bounds_fail_closed_without_padding() -> None:
    with pytest.raises(DomainValidationError, match="power-of-two"):
        walsh_hadamard_analyze((1, 2, 3))
    with pytest.raises(DomainValidationError, match="at most 1024"):
        dct_ii_analyze(tuple(0j for _ in range(1025)))
