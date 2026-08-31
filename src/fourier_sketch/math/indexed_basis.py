"""Project-owned orthonormal DCT-II and Walsh-Hadamard transforms."""

from collections.abc import Sequence
from hashlib import sha256
from math import cos, pi, sqrt

from fourier_sketch.domain import (
    BasisKind,
    DomainValidationError,
    IndexedDecomposition,
    IndexedSelection,
    IndexedTerm,
)

from ._validation import finite_complex_samples, finite_complex_value

MAX_DCT_SAMPLES = 1024
MAX_WALSH_SAMPLES = 4096


def dct_ii_analyze(
    samples: Sequence[complex],
    *,
    provenance: tuple[tuple[str, str], ...] = (),
) -> IndexedDecomposition:
    values = finite_complex_samples(samples, max_count=MAX_DCT_SAMPLES)
    count = len(values)
    terms = tuple(
        IndexedTerm(
            value=_dct_coefficient(values, index),
            index=index,
            basis=BasisKind.DCT_II,
            provenance=(*provenance, ("analysis_id", _analysis_identity(values, "dct_ii"))),
        )
        for index in range(count)
    )
    return IndexedDecomposition(
        terms=terms,
        sample_count=count,
        basis=BasisKind.DCT_II,
        provenance=provenance,
    )


def walsh_hadamard_analyze(
    samples: Sequence[complex],
    *,
    provenance: tuple[tuple[str, str], ...] = (),
) -> IndexedDecomposition:
    values = finite_complex_samples(samples, max_count=MAX_WALSH_SAMPLES)
    count = len(values)
    if count != 1 and count & (count - 1):
        raise DomainValidationError("Walsh analysis requires N=1 or a power-of-two sample count")
    normalization = 1.0 / sqrt(count)
    identity = _analysis_identity(values, "walsh_hadamard")
    terms = tuple(
        IndexedTerm(
            value=normalization
            * sum(
                value * _walsh_sign(index, sample_index)
                for sample_index, value in enumerate(values)
            ),
            index=index,
            basis=BasisKind.WALSH_HADAMARD,
            provenance=(*provenance, ("analysis_id", identity)),
        )
        for index in range(count)
    )
    return IndexedDecomposition(
        terms=terms,
        sample_count=count,
        basis=BasisKind.WALSH_HADAMARD,
        provenance=provenance,
    )


def indexed_basis_analyze(
    samples: Sequence[complex],
    basis: BasisKind,
    *,
    provenance: tuple[tuple[str, str], ...] = (),
) -> IndexedDecomposition:
    if basis is BasisKind.DCT_II:
        return dct_ii_analyze(samples, provenance=provenance)
    if basis is BasisKind.WALSH_HADAMARD:
        return walsh_hadamard_analyze(samples, provenance=provenance)
    raise DomainValidationError("indexed analysis requires DCT_II or WALSH_HADAMARD")


def dct_ii_transform(
    samples: Sequence[complex],
    *,
    provenance: tuple[tuple[str, str], ...] = (),
) -> IndexedDecomposition:
    return dct_ii_analyze(samples, provenance=provenance)


def walsh_hadamard_transform(
    samples: Sequence[complex],
    *,
    provenance: tuple[tuple[str, str], ...] = (),
) -> IndexedDecomposition:
    return walsh_hadamard_analyze(samples, provenance=provenance)


def dct_ii_synthesize(
    decomposition: IndexedDecomposition | IndexedSelection,
) -> tuple[complex, ...]:
    """Synthesize a complete or selected orthonormal DCT-II decomposition."""
    if not isinstance(decomposition, (IndexedDecomposition, IndexedSelection)):
        raise DomainValidationError(
            "decomposition must be an IndexedDecomposition or IndexedSelection"
        )
    if decomposition.basis is not BasisKind.DCT_II:
        raise DomainValidationError("DCT-II synthesis requires a DCT_II decomposition")
    return indexed_synthesize(decomposition)


def walsh_hadamard_synthesize(
    decomposition: IndexedDecomposition | IndexedSelection,
) -> tuple[complex, ...]:
    """Synthesize a complete or selected orthonormal Walsh decomposition."""
    if not isinstance(decomposition, (IndexedDecomposition, IndexedSelection)):
        raise DomainValidationError(
            "decomposition must be an IndexedDecomposition or IndexedSelection"
        )
    if decomposition.basis is not BasisKind.WALSH_HADAMARD:
        raise DomainValidationError(
            "Walsh-Hadamard synthesis requires a WALSH_HADAMARD decomposition"
        )
    return indexed_synthesize(decomposition)


def select_indexed_terms(
    decomposition: IndexedDecomposition,
    term_count: int,
) -> IndexedSelection:
    if not isinstance(decomposition, IndexedDecomposition):
        raise DomainValidationError("decomposition must be an IndexedDecomposition")
    if isinstance(term_count, bool) or not isinstance(term_count, int):
        raise DomainValidationError("indexed term_count must be an integer")
    if term_count < 1 or term_count > decomposition.sample_count:
        raise DomainValidationError(
            f"indexed term_count must be between 1 and {decomposition.sample_count}"
        )
    return IndexedSelection(
        terms=decomposition.terms[:term_count],
        sample_count=decomposition.sample_count,
        basis=decomposition.basis,
        provenance=decomposition.provenance,
        normalization=decomposition.normalization,
        ordering=decomposition.ordering,
        decomposition_id=decomposition.decomposition_id,
        source_decomposition=decomposition,
    )


def indexed_synthesize(
    selection: IndexedDecomposition | IndexedSelection,
) -> tuple[complex, ...]:
    if isinstance(selection, (IndexedDecomposition, IndexedSelection)):
        terms = selection.terms
        count = selection.sample_count
    else:
        raise DomainValidationError("selection must be an IndexedDecomposition or IndexedSelection")
    if selection.basis is BasisKind.DCT_II:
        result = tuple(_dct_contribution(term, count) for term in terms)
        return tuple(
            finite_complex_value(
                sum(values[index] for values in result),
                field_name="DCT reconstruction",
            )
            for index in range(count)
        )
    normalization = 1.0 / sqrt(count)
    values = tuple(
        normalization
        * sum(
            term.value * _walsh_sign(term.index, sample_index)
            for term in terms
        )
        for sample_index in range(count)
    )
    return tuple(
        finite_complex_value(value, field_name="Walsh reconstruction") for value in values
    )


def indexed_term_contribution(term: IndexedTerm, sample_count: int) -> tuple[complex, ...]:
    if not isinstance(term, IndexedTerm):
        raise DomainValidationError("term must be an IndexedTerm")
    if isinstance(sample_count, bool) or not isinstance(sample_count, int) or sample_count < 1:
        raise DomainValidationError("indexed sample_count must be a positive integer")
    if term.basis is BasisKind.DCT_II:
        if sample_count > MAX_DCT_SAMPLES:
            raise DomainValidationError("DCT sample_count must be at most 1024")
        return _dct_contribution(term, sample_count)
    if sample_count > MAX_WALSH_SAMPLES or sample_count & (sample_count - 1):
        raise DomainValidationError("Walsh sample_count must be a power of two at most 4096")
    if term.index >= sample_count:
        raise DomainValidationError("indexed term index exceeds sample grid")
    normalization = 1.0 / sqrt(sample_count)
    return tuple(
        finite_complex_value(
            normalization * term.value * _walsh_sign(term.index, sample_index),
            field_name="Walsh term contribution",
        )
        for sample_index in range(sample_count)
    )


def _dct_coefficient(values: tuple[complex, ...], index: int) -> complex:
    count = len(values)
    alpha = 1.0 / sqrt(count) if index == 0 else sqrt(2.0 / count)
    return finite_complex_value(
        alpha
        * sum(
            value * cos(pi * (sample_index + 0.5) * index / count)
            for sample_index, value in enumerate(values)
        ),
        field_name="DCT coefficient",
    )


def _dct_contribution(term: IndexedTerm, sample_count: int) -> tuple[complex, ...]:
    if term.index >= sample_count:
        raise DomainValidationError("indexed term index exceeds sample grid")
    alpha = 1.0 / sqrt(sample_count) if term.index == 0 else sqrt(2.0 / sample_count)
    return tuple(
        finite_complex_value(
            alpha
            * term.value
            * cos(pi * (sample_index + 0.5) * term.index / sample_count),
            field_name="DCT term contribution",
        )
        for sample_index in range(sample_count)
    )


def _walsh_sign(index: int, sample_index: int) -> int:
    return -1 if (index & sample_index).bit_count() % 2 else 1


def _analysis_identity(values: Sequence[complex], basis: str) -> str:
    payload = basis + ":" + str(len(values)) + ":" + ";".join(
        f"{value.real.hex()},{value.imag.hex()}" for value in values
    )
    return sha256(payload.encode("ascii")).hexdigest()[:24]
