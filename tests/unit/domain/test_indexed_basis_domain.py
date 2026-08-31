import pytest

from fourier_sketch.domain import (
    BasisKind,
    DomainValidationError,
    IndexedDecomposition,
    IndexedSelection,
    IndexedTerm,
)
from fourier_sketch.math import dct_ii_analyze, select_indexed_terms


def test_indexed_contract_records_basis_and_exact_owned_prefix() -> None:
    decomposition = dct_ii_analyze((1, 2, 3, 4))
    selection = select_indexed_terms(decomposition, 2)

    assert decomposition.basis is BasisKind.DCT_II
    assert tuple(term.index for term in decomposition.terms) == (0, 1, 2, 3)
    assert selection.source_decomposition is decomposition
    assert selection.terms == decomposition.terms[:2]


def test_indexed_selection_rejects_altered_value_with_copied_identity() -> None:
    decomposition = dct_ii_analyze((1, 2, 3, 4))
    original = decomposition.terms[1]
    altered = IndexedTerm(
        value=original.value + 1,
        index=original.index,
        basis=original.basis,
        provenance=original.provenance,
    )

    with pytest.raises(DomainValidationError, match="source decomposition"):
        IndexedSelection(
            terms=(decomposition.terms[0], altered),
            sample_count=4,
            basis=BasisKind.DCT_II,
            decomposition_id=decomposition.decomposition_id,
            source_decomposition=decomposition,
        )


def test_indexed_decomposition_rejects_unsupported_basis_and_shape() -> None:
    term = IndexedTerm(
        value=1,
        index=0,
        basis=BasisKind.DCT_II,
        provenance=(("analysis_id", "x"),),
    )
    with pytest.raises(DomainValidationError):
        IndexedDecomposition(terms=(term,), sample_count=1, basis=BasisKind.WALSH_HADAMARD)
