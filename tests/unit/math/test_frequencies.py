"""Unit contracts for canonical signed-frequency mapping."""

import pytest

from fourier_sketch.domain import DomainValidationError
from fourier_sketch.math import signed_frequencies, signed_frequency

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("sample_count", "expected"),
    [
        (1, (0,)),
        (2, (0, -1)),
        (3, (0, 1, -1)),
        (4, (0, 1, -2, -1)),
        (5, (0, 1, 2, -2, -1)),
    ],
)
def test_signed_frequencies_match_fft_storage_contract(
    sample_count: int,
    expected: tuple[int, ...],
) -> None:
    assert signed_frequencies(sample_count) == expected


def test_signed_frequency_rejects_invalid_count_or_index() -> None:
    with pytest.raises(DomainValidationError, match="positive integer"):
        signed_frequencies(0)
    with pytest.raises(DomainValidationError, match="0 <= index"):
        signed_frequency(2, 2)
