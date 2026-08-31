import pytest

from fourier_sketch.domain import (
    BasisKind,
    DomainValidationError,
    HaarDecomposition,
    HaarNormalization,
    HaarOrdering,
    HaarSelection,
    HaarTerm,
    HaarTermKind,
)
from fourier_sketch.math import haar_analyze, select_haar_terms


def test_haar_decomposition_records_typed_contract_and_canonical_order() -> None:
    decomposition = haar_analyze((1, 2, 3, 4))

    assert decomposition.basis is BasisKind.HAAR_WAVELET
    assert decomposition.normalization is HaarNormalization.ORTHONORMAL_1_OVER_SQRT2
    assert decomposition.ordering is HaarOrdering.ROOT_COARSE_TO_FINE
    assert [(term.kind, term.level, term.location) for term in decomposition.terms] == [
        (HaarTermKind.SCALING, 2, 0),
        (HaarTermKind.DETAIL, 1, 0),
        (HaarTermKind.DETAIL, 0, 0),
        (HaarTermKind.DETAIL, 0, 1),
    ]


def test_selection_is_an_immutable_canonical_prefix() -> None:
    decomposition = haar_analyze((1, 2, 3, 4))
    selection = select_haar_terms(decomposition, 2)

    assert isinstance(selection, HaarSelection)
    assert selection.terms == decomposition.terms[:2]
    assert selection.decomposition_id == decomposition.decomposition_id
    with pytest.raises((AttributeError, TypeError)):
        selection.terms += (decomposition.terms[2],)  # type: ignore[misc]


def test_invalid_foreign_or_noncanonical_selection_fails_closed() -> None:
    first = haar_analyze((1, 2, 3, 4))
    second = haar_analyze((4, 3, 2, 1))

    with pytest.raises(DomainValidationError, match="decomposition_id"):
        HaarSelection(
            terms=first.terms[:2],
            sample_count=4,
            provenance=second.provenance,
            decomposition_id=second.decomposition_id,
        )

    with pytest.raises(DomainValidationError, match="canonical term prefix"):
        HaarSelection(terms=(first.terms[0], first.terms[2]), sample_count=4)

    with pytest.raises(DomainValidationError, match="share provenance"):
        HaarSelection(terms=(first.terms[0], second.terms[1]), sample_count=4)

    with pytest.raises(DomainValidationError, match="source decomposition ownership"):
        HaarSelection(
            terms=first.terms[:2],
            sample_count=4,
            provenance=first.provenance,
            decomposition_id=first.decomposition_id,
        )


def test_decomposition_provenance_cannot_disagree_with_owned_terms() -> None:
    decomposition = haar_analyze((1, 2, 3, 4), provenance=(("source", "fixture"),))

    with pytest.raises(DomainValidationError, match="provenance"):
        HaarDecomposition(
            terms=decomposition.terms,
            sample_count=4,
            provenance=(("source", "different"),),
        )


def test_manual_term_rejects_non_haar_basis() -> None:
    with pytest.raises(DomainValidationError):
        HaarTerm(
            value=1,
            scale=0,
            location=0,
            basis=BasisKind.FOURIER_EPICYCLE,
        )


def test_decomposition_shape_is_bounded_and_power_of_two() -> None:
    with pytest.raises(DomainValidationError):
        HaarDecomposition(terms=(), sample_count=3)
    with pytest.raises(DomainValidationError):
        HaarDecomposition(terms=(), sample_count=8192)
