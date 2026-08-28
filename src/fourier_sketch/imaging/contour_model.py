"""Typed raster-space contour contracts for FS-012."""

from dataclasses import dataclass
from enum import StrEnum

from fourier_sketch.domain import DomainValidationError

from .edge_model import EdgeDetectionResult

MAX_CONTOUR_EDGE_PIXELS = 250_000
MAX_CONTOUR_CANDIDATES = 25_000
MAX_TOTAL_CONTOUR_POINTS = 100_000
CONTOUR_RETRIEVAL_MODE = "external"
CONTOUR_APPROXIMATION_MODE = "none"

_SAFE_BACKEND_CHARACTERS = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._+-"
)


class ContourFailureCode(StrEnum):
    """Stable fail-closed categories for the contour backend boundary."""

    INVALID_INPUT = "invalid_input"
    RESOURCE_LIMIT = "resource_limit"
    BACKEND_UNAVAILABLE = "backend_unavailable"
    BACKEND_FAILURE = "backend_failure"


class ContourExtractionError(DomainValidationError):
    """Typed contour failure that never implies a fabricated candidate."""

    def __init__(self, code: ContourFailureCode, message: str) -> None:
        if not isinstance(code, ContourFailureCode) or not isinstance(message, str) or not message:
            raise DomainValidationError("contour error requires a typed code and message")
        self.code = code
        super().__init__(message)


@dataclass(frozen=True, slots=True, order=True)
class PixelPoint:
    """One non-negative pixel-center coordinate in raster space."""

    column: int
    row: int

    def __post_init__(self) -> None:
        if type(self.column) is not int or type(self.row) is not int:
            raise DomainValidationError("pixel coordinates must be integers")
        if self.column < 0 or self.row < 0:
            raise DomainValidationError("pixel coordinates must be non-negative")


@dataclass(frozen=True, slots=True)
class ContourCandidate:
    """One cleaned, non-degenerate closed contour candidate."""

    points: tuple[PixelPoint, ...]
    signed_area2: int
    bounding_box: tuple[int, int, int, int]

    def __post_init__(self) -> None:
        if not isinstance(self.points, tuple) or any(
            not isinstance(point, PixelPoint) for point in self.points
        ):
            raise DomainValidationError("contour points must be a PixelPoint tuple")
        if len(self.points) < 3 or len(set(self.points)) != len(self.points):
            raise DomainValidationError(
                "contour candidate requires a simple cycle of unique pixels"
            )
        if self.points[0] == self.points[-1] or any(
            left == right for left, right in zip(self.points, self.points[1:], strict=False)
        ):
            raise DomainValidationError("contour candidate must not contain adjacent duplicates")
        if any(
            max(abs(left.column - right.column), abs(left.row - right.row)) > 1
            for left, right in zip(
                self.points,
                (*self.points[1:], self.points[0]),
                strict=True,
            )
        ):
            raise DomainValidationError("contour candidate must be an adjacent closed cycle")
        if type(self.signed_area2) is not int or self.signed_area2 == 0:
            raise DomainValidationError("contour candidate requires non-zero exact area")
        if self.signed_area2 != signed_shoelace_area2(self.points):
            raise DomainValidationError("contour candidate area does not match its points")
        if self.bounding_box != contour_bounding_box(self.points):
            raise DomainValidationError("contour candidate bounding box does not match its points")

    @property
    def point_count(self) -> int:
        return len(self.points)

    @property
    def absolute_area2(self) -> int:
        return abs(self.signed_area2)

    @property
    def bounding_box_area(self) -> int:
        minimum_column, minimum_row, maximum_column, maximum_row = self.bounding_box
        return (maximum_column - minimum_column + 1) * (maximum_row - minimum_row + 1)


@dataclass(frozen=True, slots=True)
class ContourExtractionResult:
    """Bounded external candidates with exact backend and source provenance."""

    candidates: tuple[ContourCandidate, ...]
    source: EdgeDetectionResult
    backend: str
    retrieval_mode: str = CONTOUR_RETRIEVAL_MODE
    approximation_mode: str = CONTOUR_APPROXIMATION_MODE

    def __post_init__(self) -> None:
        if not isinstance(self.candidates, tuple) or any(
            not isinstance(candidate, ContourCandidate) for candidate in self.candidates
        ):
            raise DomainValidationError("contour candidates must be a typed tuple")
        if len(self.candidates) > MAX_CONTOUR_CANDIDATES:
            raise DomainValidationError("contour candidate count exceeds the budget")
        if sum(candidate.point_count for candidate in self.candidates) > MAX_TOTAL_CONTOUR_POINTS:
            raise DomainValidationError("contour candidate points exceed the budget")
        if not isinstance(self.source, EdgeDetectionResult):
            raise DomainValidationError("contour extraction requires an edge result")
        if not _safe_opencv_backend(self.backend):
            raise DomainValidationError("contour backend provenance is invalid")
        if self.retrieval_mode != CONTOUR_RETRIEVAL_MODE:
            raise DomainValidationError("contour retrieval mode must be external")
        if self.approximation_mode != CONTOUR_APPROXIMATION_MODE:
            raise DomainValidationError("contour approximation mode must be none")
        width, height = self.source.source_dimensions
        if any(
            point.column >= width or point.row >= height
            for candidate in self.candidates
            for point in candidate.points
        ):
            raise DomainValidationError("contour candidate lies outside its source raster")
        if any(
            self.source.edges.pixels[point.row * width + point.column] != 255
            for candidate in self.candidates
            for point in candidate.points
        ):
            raise DomainValidationError("contour candidate must reference source edge pixels")

    @property
    def candidate_count(self) -> int:
        return len(self.candidates)

    @property
    def total_candidate_points(self) -> int:
        return sum(candidate.point_count for candidate in self.candidates)


def signed_shoelace_area2(points: tuple[PixelPoint, ...]) -> int:
    """Return exact signed twice-area in raster coordinates."""
    if not isinstance(points, tuple) or any(not isinstance(point, PixelPoint) for point in points):
        raise DomainValidationError("shoelace points must be a PixelPoint tuple")
    if len(points) < 3:
        return 0
    return sum(
        left.column * right.row - right.column * left.row
        for left, right in zip(points, (*points[1:], points[0]), strict=True)
    )


def contour_bounding_box(points: tuple[PixelPoint, ...]) -> tuple[int, int, int, int]:
    """Return an inclusive raster bounding box."""
    if not isinstance(points, tuple) or not points or any(
        not isinstance(point, PixelPoint) for point in points
    ):
        raise DomainValidationError("bounding box requires PixelPoint values")
    columns = tuple(point.column for point in points)
    rows = tuple(point.row for point in points)
    return min(columns), min(rows), max(columns), max(rows)


def _safe_opencv_backend(value: str) -> bool:
    if not isinstance(value, str) or not value.startswith("opencv/"):
        return False
    version = value.removeprefix("opencv/")
    return (
        1 <= len(version) <= 64
        and version[0] in _SAFE_BACKEND_CHARACTERS
        and all(character in _SAFE_BACKEND_CHARACTERS for character in version)
    )
