"""Project-owned orthonormal complex Haar analysis and synthesis."""

from collections.abc import Sequence
from hashlib import sha256
from math import isfinite, sqrt

from fourier_sketch.domain import (
    BasisKind,
    DomainValidationError,
    HaarDecomposition,
    HaarSelection,
    HaarTerm,
    HaarTermKind,
)

from ._validation import finite_complex_samples, finite_complex_value

MAX_HAAR_SAMPLES = 4096
_INV_SQRT_TWO = 1.0 / sqrt(2.0)


def haar_analyze(
    samples: Sequence[complex],
    *,
    provenance: tuple[tuple[str, str], ...] = (),
) -> HaarDecomposition:
    """Analyze a finite complex sample sequence with the canonical Haar basis."""
    values = finite_complex_samples(samples, max_count=MAX_HAAR_SAMPLES)
    count = len(values)
    if count != 1 and (count & (count - 1)) != 0:
        raise DomainValidationError("Haar analysis requires N=1 or a power-of-two sample count")

    levels = count.bit_length() - 1
    identity = _analysis_identity(values)
    term_provenance = (*provenance, ("analysis_id", identity))
    current = values
    details: dict[int, tuple[complex, ...]] = {}
    for scale in range(levels):
        approximation: list[complex] = []
        detail: list[complex] = []
        for index in range(0, len(current), 2):
            approximation.append((current[index] + current[index + 1]) * _INV_SQRT_TWO)
            detail.append((current[index] - current[index + 1]) * _INV_SQRT_TWO)
        current = tuple(approximation)
        details[scale] = tuple(detail)

    terms: list[HaarTerm] = [
        HaarTerm(
            value=current[0],
            scale=levels,
            location=0,
            kind=HaarTermKind.SCALING,
            provenance=term_provenance,
        )
    ]
    for scale in range(levels - 1, -1, -1):
        terms.extend(
            HaarTerm(
                value=value,
                scale=scale,
                location=location,
                kind=HaarTermKind.DETAIL,
                provenance=term_provenance,
            )
            for location, value in enumerate(details[scale])
        )
    return HaarDecomposition(
        terms=tuple(terms),
        sample_count=count,
        basis=BasisKind.HAAR_WAVELET,
        provenance=provenance,
    )


def haar_transform(
    samples: Sequence[complex],
    *,
    provenance: tuple[tuple[str, str], ...] = (),
) -> HaarDecomposition:
    """Alias for :func:`haar_analyze` used by numerical callers."""
    return haar_analyze(samples, provenance=provenance)


def select_haar_terms(decomposition: HaarDecomposition, term_count: int) -> HaarSelection:
    """Select the canonical root-scaling/coarse-to-fine prefix."""
    if not isinstance(decomposition, HaarDecomposition):
        raise DomainValidationError("decomposition must be a HaarDecomposition")
    if isinstance(term_count, bool) or not isinstance(term_count, int):
        raise DomainValidationError("Haar term_count must be an integer")
    if term_count < 1 or term_count > decomposition.sample_count:
        raise DomainValidationError(
            f"Haar term_count must be between 1 and {decomposition.sample_count}"
        )
    return HaarSelection(
        terms=decomposition.terms[:term_count],
        sample_count=decomposition.sample_count,
        basis=decomposition.basis,
        provenance=decomposition.provenance,
        normalization=decomposition.normalization,
        ordering=decomposition.ordering,
        decomposition_id=decomposition.decomposition_id,
        source_decomposition=decomposition,
    )


def haar_synthesize(selection: HaarDecomposition | HaarSelection) -> tuple[complex, ...]:
    """Synthesize a complete or selected Haar coefficient set on its analysis grid."""
    if isinstance(selection, HaarDecomposition):
        terms = selection.terms
        count = selection.sample_count
    elif isinstance(selection, HaarSelection):
        terms = selection.terms
        count = selection.sample_count
        term_id = next(
            (value for key, value in terms[0].provenance if key == "analysis_id"),
            None,
        )
        if term_id is not None and selection.decomposition_id != term_id:
            raise DomainValidationError("Haar selection does not own its coefficient terms")
    else:
        raise DomainValidationError("selection must be a HaarDecomposition or HaarSelection")
    return _synthesize_terms(terms, count)


def haar_synthesize_samples(selection: HaarDecomposition | HaarSelection) -> tuple[complex, ...]:
    """Explicitly named synthesis alias for callers that work with sample grids."""
    return haar_synthesize(selection)


def haar_term_contribution(term: HaarTerm, sample_count: int) -> tuple[complex, ...]:
    """Return the sample-grid contribution of exactly one Haar term."""
    if not isinstance(term, HaarTerm):
        raise DomainValidationError("term must be a HaarTerm")
    if isinstance(sample_count, bool) or not isinstance(sample_count, int):
        raise DomainValidationError("Haar sample_count must be an integer")
    if sample_count < 1 or sample_count > MAX_HAAR_SAMPLES:
        raise DomainValidationError("Haar sample_count is outside the Haar budget")
    if sample_count != 1 and (sample_count & (sample_count - 1)) != 0:
        raise DomainValidationError("Haar sample_count must be a power of two")
    levels = sample_count.bit_length() - 1
    if term.scale > levels:
        raise DomainValidationError("Haar term scale exceeds sample grid")
    if term.kind is HaarTermKind.SCALING and (term.scale != levels or term.location != 0):
        raise DomainValidationError("Haar scaling term does not belong to sample grid")
    if term.kind is HaarTermKind.DETAIL and (
        term.scale >= levels or term.location >= (1 << (levels - term.scale - 1))
    ):
        raise DomainValidationError("Haar detail location exceeds its scale")
    return _synthesize_terms((term,), sample_count)


def _synthesize_terms(terms: Sequence[HaarTerm], sample_count: int) -> tuple[complex, ...]:
    levels = sample_count.bit_length() - 1
    by_key = {(term.kind, term.scale, term.location): term.value for term in terms}
    root = by_key.get((HaarTermKind.SCALING, levels, 0), 0j)
    current: tuple[complex, ...] = (root,)
    for scale in range(levels - 1, -1, -1):
        next_values: list[complex] = []
        for location, approximation in enumerate(current):
            detail = by_key.get((HaarTermKind.DETAIL, scale, location), 0j)
            next_values.extend(
                ((approximation + detail) * _INV_SQRT_TWO,
                 (approximation - detail) * _INV_SQRT_TWO)
            )
        current = tuple(next_values)
    result = tuple(
        finite_complex_value(value, field_name="Haar reconstruction") for value in current
    )
    if len(result) != sample_count or any(not isfinite(value.real) for value in result):
        raise DomainValidationError("Haar reconstruction is outside the finite domain")
    return result


def _analysis_identity(values: Sequence[complex]) -> str:
    payload = str(len(values)) + ":" + ";".join(
        f"{value.real.hex()},{value.imag.hex()}" for value in values
    )
    return sha256(payload.encode("ascii")).hexdigest()[:24]
