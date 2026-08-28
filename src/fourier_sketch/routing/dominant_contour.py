"""Deterministic dominant-contour selection and curve normalization."""

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite

from fourier_sketch.domain import Curve, DomainValidationError, Point2D
from fourier_sketch.imaging.contour_model import (
    ContourCandidate,
    ContourExtractionResult,
    PixelPoint,
)

DOMINANT_SELECTION_POLICY = "area2-bbox-points-canonical-v1"
COORDINATE_TRANSFORM_ID = "pixel-center-centered-aspect-v1"
ORIENTATION_POLICY = "counter-clockwise-domain"
START_POINT_POLICY = "topmost-leftmost-raster"


class NoContourReason(StrEnum):
    """Observable reasons for a valid empty contour result."""

    EMPTY_EDGE_MAP = "empty_edge_map"
    NO_USABLE_CANDIDATES = "no_usable_candidates"


@dataclass(frozen=True, slots=True)
class NoContourResult:
    """A valid empty result that carries extraction provenance."""

    extraction: ContourExtractionResult
    reason: NoContourReason

    def __post_init__(self) -> None:
        if not isinstance(self.extraction, ContourExtractionResult) or not isinstance(
            self.reason, NoContourReason
        ):
            raise DomainValidationError("no-contour result requires typed provenance")
        expected = (
            NoContourReason.EMPTY_EDGE_MAP
            if self.extraction.source.is_empty
            else NoContourReason.NO_USABLE_CANDIDATES
        )
        if self.extraction.candidates or self.reason is not expected:
            raise DomainValidationError("no-contour reason is inconsistent with extraction")


@dataclass(frozen=True, slots=True)
class DominantContourSelection:
    """One selected candidate with an explicit project-owned policy."""

    extraction: ContourExtractionResult
    candidate: ContourCandidate
    policy: str = DOMINANT_SELECTION_POLICY

    def __post_init__(self) -> None:
        if not isinstance(self.extraction, ContourExtractionResult) or not isinstance(
            self.candidate, ContourCandidate
        ):
            raise DomainValidationError("dominant selection requires typed contour values")
        if self.candidate not in self.extraction.candidates:
            raise DomainValidationError("selected contour must come from the extraction result")
        if self.policy != DOMINANT_SELECTION_POLICY:
            raise DomainValidationError("dominant selection policy is invalid")


@dataclass(frozen=True, slots=True)
class NormalizedContourProvenance:
    """Deterministic raster-to-domain decisions for the selected contour."""

    source_dimensions: tuple[int, int]
    scale: float
    coordinate_transform: str
    orientation: str
    start_point: str
    selection_policy: str
    extraction_backend: str
    candidate_count: int
    selected_absolute_area2: int
    selected_bounding_box: tuple[int, int, int, int]
    selected_point_count: int

    def __post_init__(self) -> None:
        if (
            not isinstance(self.source_dimensions, tuple)
            or len(self.source_dimensions) != 2
            or any(type(value) is not int or value < 1 for value in self.source_dimensions)
        ):
            raise DomainValidationError("contour source dimensions must be positive integers")
        if not isinstance(self.scale, float) or not isfinite(self.scale) or self.scale <= 0.0:
            raise DomainValidationError("contour coordinate scale must be positive and finite")
        if self.coordinate_transform != COORDINATE_TRANSFORM_ID:
            raise DomainValidationError("contour coordinate transform is invalid")
        if self.orientation != ORIENTATION_POLICY or self.start_point != START_POINT_POLICY:
            raise DomainValidationError("contour normalization policy is invalid")
        if self.selection_policy != DOMINANT_SELECTION_POLICY:
            raise DomainValidationError("contour selection provenance is invalid")
        if not isinstance(self.extraction_backend, str) or not self.extraction_backend:
            raise DomainValidationError("contour extraction backend must be recorded")
        if type(self.candidate_count) is not int or self.candidate_count < 1:
            raise DomainValidationError("contour candidate count must be positive")
        if type(self.selected_absolute_area2) is not int or self.selected_absolute_area2 < 1:
            raise DomainValidationError("selected contour area must be positive")
        if type(self.selected_point_count) is not int or self.selected_point_count < 3:
            raise DomainValidationError("selected contour point count must be at least three")


@dataclass(frozen=True, slots=True)
class NormalizedContourCurve:
    """Canonical closed domain curve and its complete selection/transform provenance."""

    selection: DominantContourSelection
    curve: Curve
    provenance: NormalizedContourProvenance

    def __post_init__(self) -> None:
        if not isinstance(self.selection, DominantContourSelection):
            raise DomainValidationError("normalized contour requires a dominant selection")
        if not isinstance(self.curve, Curve) or not self.curve.closed:
            raise DomainValidationError("normalized contour curve must be closed")
        if self.curve.sample_count != self.selection.candidate.point_count:
            raise DomainValidationError("normalized curve must preserve selected point count")
        if not isinstance(self.provenance, NormalizedContourProvenance):
            raise DomainValidationError("normalized contour provenance is required")
        candidate = self.selection.candidate
        extraction = self.selection.extraction
        expected = NormalizedContourProvenance(
            source_dimensions=extraction.source.source_dimensions,
            scale=2.0 / max(
                extraction.source.source_dimensions[0] - 1,
                extraction.source.source_dimensions[1] - 1,
            ),
            coordinate_transform=COORDINATE_TRANSFORM_ID,
            orientation=ORIENTATION_POLICY,
            start_point=START_POINT_POLICY,
            selection_policy=self.selection.policy,
            extraction_backend=extraction.backend,
            candidate_count=extraction.candidate_count,
            selected_absolute_area2=candidate.absolute_area2,
            selected_bounding_box=candidate.bounding_box,
            selected_point_count=candidate.point_count,
        )
        if self.provenance != expected:
            raise DomainValidationError("normalized contour provenance is inconsistent")
        expected_points = _domain_points(
            _canonical_oriented_points(candidate),
            extraction.source.source_dimensions,
            self.provenance.scale,
        )
        if self.curve.points != expected_points:
            raise DomainValidationError("normalized contour curve is not canonical")


def select_dominant_contour(
    extraction: ContourExtractionResult,
) -> DominantContourSelection | NoContourResult:
    """Select one contour independently of backend candidate ordering."""
    if not isinstance(extraction, ContourExtractionResult):
        raise DomainValidationError("dominant selection requires a contour extraction result")
    if not extraction.candidates:
        reason = (
            NoContourReason.EMPTY_EDGE_MAP
            if extraction.source.is_empty
            else NoContourReason.NO_USABLE_CANDIDATES
        )
        return NoContourResult(extraction=extraction, reason=reason)

    selected = extraction.candidates[0]
    selected_primary = _primary_selection_key(selected)
    selected_signature: tuple[tuple[int, int], ...] | None = None
    for candidate in extraction.candidates[1:]:
        candidate_primary = _primary_selection_key(candidate)
        if candidate_primary < selected_primary:
            selected = candidate
            selected_primary = candidate_primary
            selected_signature = None
            continue
        if candidate_primary != selected_primary:
            continue
        candidate_signature = canonical_pixel_signature(candidate.points)
        if selected_signature is None:
            selected_signature = canonical_pixel_signature(selected.points)
        if candidate_signature < selected_signature:
            selected = candidate
            selected_signature = candidate_signature
    return DominantContourSelection(extraction=extraction, candidate=selected)


def normalize_selected_contour(selection: DominantContourSelection) -> NormalizedContourCurve:
    """Map pixel centers to a centered, aspect-preserving, canonical closed Curve."""
    if not isinstance(selection, DominantContourSelection):
        raise DomainValidationError("contour normalization requires a dominant selection")
    width, height = selection.extraction.source.source_dimensions
    maximum_span = max(width - 1, height - 1)
    if maximum_span < 1:
        raise DomainValidationError("selected contour requires a non-zero raster span")
    scale = 2.0 / maximum_span

    raster_points = _canonical_oriented_points(selection.candidate)
    curve = Curve(_domain_points(raster_points, (width, height), scale), closed=True)
    provenance = NormalizedContourProvenance(
        source_dimensions=(width, height),
        scale=float(scale),
        coordinate_transform=COORDINATE_TRANSFORM_ID,
        orientation=ORIENTATION_POLICY,
        start_point=START_POINT_POLICY,
        selection_policy=selection.policy,
        extraction_backend=selection.extraction.backend,
        candidate_count=selection.extraction.candidate_count,
        selected_absolute_area2=selection.candidate.absolute_area2,
        selected_bounding_box=selection.candidate.bounding_box,
        selected_point_count=selection.candidate.point_count,
    )
    return NormalizedContourCurve(selection=selection, curve=curve, provenance=provenance)


def canonical_pixel_signature(points: tuple[PixelPoint, ...]) -> tuple[tuple[int, int], ...]:
    """Return a cyclic- and reversal-invariant raster signature in O(n)."""
    if not isinstance(points, tuple) or not points or any(
        not isinstance(point, PixelPoint) for point in points
    ):
        raise DomainValidationError("canonical signature requires PixelPoint values")
    forward = tuple((point.row, point.column) for point in points)
    reverse = tuple(reversed(forward))
    canonical_forward = _minimal_rotation(forward)
    canonical_reverse = _minimal_rotation(reverse)
    return min(canonical_forward, canonical_reverse)


def _primary_selection_key(candidate: ContourCandidate) -> tuple[int, int, int]:
    return (
        -candidate.absolute_area2,
        -candidate.bounding_box_area,
        -candidate.point_count,
    )


def _canonical_oriented_points(candidate: ContourCandidate) -> tuple[PixelPoint, ...]:
    points = candidate.points
    if candidate.signed_area2 > 0:
        points = tuple(reversed(points))
    return _rotate_to_minimum(points)


def _domain_points(
    raster_points: tuple[PixelPoint, ...],
    source_dimensions: tuple[int, int],
    scale: float,
) -> tuple[Point2D, ...]:
    width, height = source_dimensions
    center_column = (width - 1) / 2.0
    center_row = (height - 1) / 2.0
    return tuple(
        Point2D(
            (point.column - center_column) * scale,
            (center_row - point.row) * scale,
        )
        for point in raster_points
    )


def _rotate_to_minimum(points: tuple[PixelPoint, ...]) -> tuple[PixelPoint, ...]:
    signature = tuple((point.row, point.column) for point in points)
    index = _minimal_rotation_index(signature)
    return points[index:] + points[:index]


def _minimal_rotation(
    sequence: tuple[tuple[int, int], ...],
) -> tuple[tuple[int, int], ...]:
    index = _minimal_rotation_index(sequence)
    return sequence[index:] + sequence[:index]


def _minimal_rotation_index(sequence: tuple[tuple[int, int], ...]) -> int:
    """Booth-style lexicographically minimal cyclic rotation index."""
    size = len(sequence)
    if size < 2:
        return 0
    doubled = sequence + sequence
    left = 0
    right = 1
    offset = 0
    while left < size and right < size and offset < size:
        left_value = doubled[left + offset]
        right_value = doubled[right + offset]
        if left_value == right_value:
            offset += 1
            continue
        if left_value > right_value:
            left = left + offset + 1
            if left == right:
                left += 1
        else:
            right = right + offset + 1
            if right == left:
                right += 1
        offset = 0
    return min(left, right)
