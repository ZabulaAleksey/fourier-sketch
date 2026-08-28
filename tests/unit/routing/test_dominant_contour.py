"""Project-owned FS-012 dominant selection and normalization tests."""

from collections.abc import Iterable

import pytest

from fourier_sketch.imaging import (
    ContourCandidate,
    ContourExtractionResult,
    PixelPoint,
    RasterImage,
    RasterStage,
    contour_bounding_box,
    detect_threshold_boundary,
    signed_shoelace_area2,
)
from fourier_sketch.routing import (
    NoContourReason,
    NoContourResult,
    canonical_pixel_signature,
    normalize_selected_contour,
    select_dominant_contour,
)

pytestmark = pytest.mark.unit


def _candidate(coordinates: Iterable[tuple[int, int]]) -> ContourCandidate:
    points = tuple(PixelPoint(column, row) for column, row in coordinates)
    return ContourCandidate(
        points=points,
        signed_area2=signed_shoelace_area2(points),
        bounding_box=contour_bounding_box(points),
    )


def _extraction(
    *candidates: ContourCandidate,
    width: int = 8,
    height: int = 6,
    empty_edges: bool = False,
) -> ContourExtractionResult:
    pixels = bytes(width * height) if empty_edges else bytes([255]) * (width * height)
    edges = detect_threshold_boundary(RasterImage(width, height, pixels, RasterStage.BINARY))
    return ContourExtractionResult(
        candidates=tuple(candidates),
        source=edges,
        backend="opencv/5.0-test",
    )


def test_dominant_selection_uses_area_then_bbox_then_point_count() -> None:
    square = _candidate(((0, 0), (2, 0), (2, 2), (0, 2)))
    equal_area_larger_box = _candidate(((0, 0), (4, 0), (0, 2)))
    equal_area_box_more_points = _candidate(((0, 0), (2, 0), (2, 1), (2, 2), (0, 2)))

    bbox_winner = select_dominant_contour(_extraction(square, equal_area_larger_box))
    points_winner = select_dominant_contour(_extraction(square, equal_area_box_more_points))

    assert bbox_winner.candidate == equal_area_larger_box  # type: ignore[union-attr]
    assert points_winner.candidate == equal_area_box_more_points  # type: ignore[union-attr]


def test_exact_tie_uses_canonical_signature_not_backend_order() -> None:
    first = _candidate(((0, 0), (2, 0), (2, 2), (0, 2)))
    second = _candidate(
        tuple((point.column, point.row) for point in reversed(first.points))
    )

    left = select_dominant_contour(_extraction(first, second))
    right = select_dominant_contour(_extraction(second, first))

    assert not isinstance(left, NoContourResult)
    assert not isinstance(right, NoContourResult)
    assert canonical_pixel_signature(left.candidate.points) == canonical_pixel_signature(
        right.candidate.points
    )


def test_normalization_is_counter_clockwise_and_starts_topmost_leftmost() -> None:
    clockwise_raster = _candidate(((1, 0), (3, 0), (3, 2), (1, 2)))
    selection = select_dominant_contour(
        _extraction(clockwise_raster, width=5, height=3)
    )

    assert not isinstance(selection, NoContourResult)
    normalized = normalize_selected_contour(selection)

    assert normalized.curve.closed
    assert normalized.curve.start.x == pytest.approx(-0.5)
    assert normalized.curve.start.y == pytest.approx(0.5)
    domain_area2 = sum(
        left.x * right.y - right.x * left.y
        for left, right in zip(
            normalized.curve.points,
            (*normalized.curve.points[1:], normalized.curve.points[0]),
            strict=True,
        )
    )
    assert domain_area2 > 0.0
    assert normalized.provenance.scale == pytest.approx(0.5)


@pytest.mark.parametrize("reverse", (False, True))
@pytest.mark.parametrize("shift", range(4))
def test_normalized_curve_is_invariant_to_candidate_rotation_and_direction(
    shift: int,
    reverse: bool,
) -> None:
    base = ((1, 0), (3, 0), (3, 2), (1, 2))
    variant = tuple(reversed(base)) if reverse else base
    variant = variant[shift:] + variant[:shift]
    selection = select_dominant_contour(
        _extraction(_candidate(variant), width=5, height=3)
    )
    expected_selection = select_dominant_contour(
        _extraction(_candidate(base), width=5, height=3)
    )

    assert not isinstance(selection, NoContourResult)
    assert not isinstance(expected_selection, NoContourResult)
    assert normalize_selected_contour(selection).curve == normalize_selected_contour(
        expected_selection
    ).curve


@pytest.mark.parametrize("empty_edges", (True, False))
def test_empty_candidates_are_explicit_no_contour(empty_edges: bool) -> None:
    result = select_dominant_contour(_extraction(empty_edges=empty_edges))

    assert isinstance(result, NoContourResult)
    expected = (
        NoContourReason.EMPTY_EDGE_MAP
        if empty_edges
        else NoContourReason.NO_USABLE_CANDIDATES
    )
    assert result.reason is expected
