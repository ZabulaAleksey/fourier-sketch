from math import sqrt

import pytest

from fourier_sketch.domain import DomainValidationError, HaarSelection
from fourier_sketch.math import (
    haar_analyze,
    haar_synthesize,
    haar_term_contribution,
    select_haar_terms,
)


@pytest.mark.parametrize(
    "samples",
    [
        (2,),
        (1, 1, 1, 1),
        (1, 0, 0, 0),
        (1, 1, -1, -1),
        (1 + 2j, -0.5j, 0.25 - 1j, -2 + 0.5j),
    ],
)
def test_full_haar_round_trip(samples: tuple[complex, ...]) -> None:
    decomposition = haar_analyze(samples)
    result = haar_synthesize(decomposition)

    assert result == pytest.approx(samples, abs=1e-12)


def test_n2_coefficients_use_orthonormal_pair() -> None:
    decomposition = haar_analyze((1, 3))

    assert decomposition.scaling_term.value == pytest.approx(4 / sqrt(2))
    assert decomposition.detail_terms[0].value == pytest.approx(-2 / sqrt(2))


def test_n8_term_lattice_is_root_then_coarse_to_fine() -> None:
    decomposition = haar_analyze(tuple(range(8)))

    assert [(term.scale, term.location) for term in decomposition.detail_terms] == [
        (2, 0),
        (1, 0),
        (1, 1),
        (0, 0),
        (0, 1),
        (0, 2),
        (0, 3),
    ]


def test_partial_selection_zeroes_unselected_coefficients() -> None:
    decomposition = haar_analyze((1, 2, 3, 4))
    selected = select_haar_terms(decomposition, 2)

    assert haar_synthesize(selected) == pytest.approx((1.5, 1.5, 3.5, 3.5), abs=1e-12)


def test_single_term_contribution_sums_to_full_reconstruction() -> None:
    decomposition = haar_analyze((1, 2, 3, 4))
    contributions = tuple(
        haar_term_contribution(term, 4) for term in decomposition.terms
    )
    total = tuple(sum(contribution[index] for contribution in contributions) for index in range(4))

    assert total == pytest.approx(haar_synthesize(decomposition), abs=1e-12)


def test_foreign_selection_identity_is_rejected_by_synthesis() -> None:
    first = haar_analyze((1, 2, 3, 4))
    second = haar_analyze((4, 3, 2, 1))
    with pytest.raises(DomainValidationError, match="does not own"):
        foreign = HaarSelection(
            terms=first.terms[:2],
            sample_count=4,
            decomposition_id=second.decomposition_id,
        )
        haar_synthesize(foreign)


def test_altered_value_with_copied_identity_is_rejected() -> None:
    decomposition = haar_analyze((1, 2, 3, 4))
    altered = decomposition.terms[1]
    altered = type(altered)(
        value=altered.value + 1,
        scale=altered.scale,
        location=altered.location,
        kind=altered.kind,
        provenance=altered.provenance,
    )
    with pytest.raises(DomainValidationError, match="source decomposition"):
        HaarSelection(
            terms=(decomposition.terms[0], altered),
            sample_count=4,
            decomposition_id=decomposition.decomposition_id,
            source_decomposition=decomposition,
        )


@pytest.mark.parametrize("samples", [(1, 2, 3), (1, 2, 3, 4, 5)])
def test_non_power_of_two_fails_without_padding(samples: tuple[int, ...]) -> None:
    with pytest.raises(DomainValidationError, match="power-of-two"):
        haar_analyze(samples)


def test_non_finite_and_oversized_inputs_fail_closed() -> None:
    with pytest.raises(DomainValidationError):
        haar_analyze((complex(float("nan")),))
    with pytest.raises(DomainValidationError, match="at most 4096"):
        haar_analyze(tuple(0j for _ in range(4097)))
