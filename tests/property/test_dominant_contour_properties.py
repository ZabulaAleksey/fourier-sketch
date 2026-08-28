"""Generative invariants for canonical FS-012 contour policy."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from fourier_sketch.imaging import PixelPoint
from fourier_sketch.routing import canonical_pixel_signature

pytestmark = pytest.mark.property

_SQUARE = (PixelPoint(1, 1), PixelPoint(4, 1), PixelPoint(4, 4), PixelPoint(1, 4))


@given(shift=st.integers(min_value=0, max_value=3), reverse=st.booleans())
def test_signature_is_invariant_to_cyclic_shift_and_reversal(
    shift: int,
    reverse: bool,
) -> None:
    points = tuple(reversed(_SQUARE)) if reverse else _SQUARE
    shifted = points[shift:] + points[:shift]

    assert canonical_pixel_signature(shifted) == canonical_pixel_signature(_SQUARE)
