"""FS-012 raster-space contour contract tests."""

import pytest

from fourier_sketch.domain import DomainValidationError
from fourier_sketch.imaging import (
    ContourCandidate,
    PixelPoint,
    contour_bounding_box,
    signed_shoelace_area2,
)

pytestmark = pytest.mark.unit


def test_candidate_records_exact_area_and_inclusive_bounds() -> None:
    points = (
        PixelPoint(1, 1),
        PixelPoint(4, 1),
        PixelPoint(4, 3),
        PixelPoint(1, 3),
    )

    candidate = ContourCandidate(
        points=points,
        signed_area2=signed_shoelace_area2(points),
        bounding_box=contour_bounding_box(points),
    )

    assert candidate.signed_area2 == 12
    assert candidate.absolute_area2 == 12
    assert candidate.bounding_box == (1, 1, 4, 3)
    assert candidate.bounding_box_area == 12


@pytest.mark.parametrize(
    "points",
    (
        (PixelPoint(0, 0), PixelPoint(1, 0)),
        (PixelPoint(0, 0), PixelPoint(1, 0), PixelPoint(2, 0)),
        (PixelPoint(0, 0), PixelPoint(1, 0), PixelPoint(1, 0), PixelPoint(0, 1)),
    ),
)
def test_candidate_rejects_degenerate_or_duplicate_sequences(
    points: tuple[PixelPoint, ...],
) -> None:
    with pytest.raises(DomainValidationError):
        ContourCandidate(
            points=points,
            signed_area2=signed_shoelace_area2(points),
            bounding_box=contour_bounding_box(points),
        )


def test_pixel_point_rejects_negative_or_boolean_coordinates() -> None:
    with pytest.raises(DomainValidationError):
        PixelPoint(-1, 0)
    with pytest.raises(DomainValidationError):
        PixelPoint(True, 0)
