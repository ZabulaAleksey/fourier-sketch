"""Backend-neutral contracts for FS-011 edge intermediates."""

from dataclasses import dataclass
from enum import StrEnum

from fourier_sketch.domain import DomainValidationError

from .model import MAX_DECODED_IMAGE_PIXELS, RasterImage, RasterStage

_SAFE_BACKEND_CHARACTERS = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._+-"
)


class EdgeAlgorithm(StrEnum):
    """Explicitly different edge semantics available in FS-011."""

    THRESHOLD_BOUNDARY = "threshold_boundary"
    CANNY = "canny"


class BoundaryConnectivity(StrEnum):
    """Neighborhood used to decide whether a foreground pixel is interior."""

    FOUR = "4"
    EIGHT = "8"


class EdgeFailureCode(StrEnum):
    """Stable error categories for algorithm and backend boundaries."""

    INVALID_INPUT = "invalid_input"
    INVALID_PARAMETERS = "invalid_parameters"
    BACKEND_UNAVAILABLE = "backend_unavailable"
    BACKEND_FAILURE = "backend_failure"


class EdgeDetectionError(DomainValidationError):
    """Typed edge failure that never implies a contour result."""

    def __init__(self, code: EdgeFailureCode, message: str) -> None:
        if not isinstance(code, EdgeFailureCode) or not isinstance(message, str) or not message:
            raise DomainValidationError("edge error requires a typed code and message")
        self.code = code
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class ThresholdBoundaryParameters:
    """Parameters of the project-owned foreground-side boundary transform."""

    connectivity: BoundaryConnectivity = BoundaryConnectivity.EIGHT

    def __post_init__(self) -> None:
        if not isinstance(self.connectivity, BoundaryConnectivity):
            raise EdgeDetectionError(
                EdgeFailureCode.INVALID_PARAMETERS,
                "boundary connectivity must be 4 or 8",
            )


@dataclass(frozen=True, slots=True)
class CannyParameters:
    """Validated OpenCV Canny parameters for an 8-bit grayscale raster."""

    low_threshold: int = 100
    high_threshold: int = 200
    aperture_size: int = 3
    l2_gradient: bool = True

    def __post_init__(self) -> None:
        if (
            type(self.low_threshold) is not int
            or type(self.high_threshold) is not int
            or not 0 <= self.low_threshold < self.high_threshold <= 255
        ):
            raise EdgeDetectionError(
                EdgeFailureCode.INVALID_PARAMETERS,
                "Canny thresholds must satisfy 0 <= low < high <= 255",
            )
        if type(self.aperture_size) is not int or self.aperture_size not in (3, 5, 7):
            raise EdgeDetectionError(
                EdgeFailureCode.INVALID_PARAMETERS,
                "Canny aperture size must be 3, 5 or 7",
            )
        if type(self.l2_gradient) is not bool:
            raise EdgeDetectionError(
                EdgeFailureCode.INVALID_PARAMETERS,
                "Canny L2 gradient choice must be boolean",
            )


EdgeParameters = ThresholdBoundaryParameters | CannyParameters


@dataclass(frozen=True, slots=True)
class EdgeDetectionResult:
    """Immutable binary edge map with exact algorithm/backend provenance."""

    edges: RasterImage
    algorithm: EdgeAlgorithm
    backend: str
    parameters: EdgeParameters
    source_stage: RasterStage
    source_dimensions: tuple[int, int]

    def __post_init__(self) -> None:
        if not isinstance(self.edges, RasterImage) or self.edges.stage is not RasterStage.BINARY:
            raise DomainValidationError("edge result must contain a typed binary raster")
        if not isinstance(self.algorithm, EdgeAlgorithm):
            raise DomainValidationError("edge algorithm must be explicit")
        if not isinstance(self.backend, str) or not self.backend:
            raise DomainValidationError("edge backend must be recorded")
        if not isinstance(self.source_stage, RasterStage):
            raise DomainValidationError("edge source stage must be explicit")
        _validate_dimensions(self.source_dimensions)
        if self.source_dimensions != (self.edges.width, self.edges.height):
            raise DomainValidationError("edge dimensions must match source dimensions")
        if self.algorithm is EdgeAlgorithm.THRESHOLD_BOUNDARY:
            if not isinstance(self.parameters, ThresholdBoundaryParameters):
                raise DomainValidationError("threshold boundary parameters are required")
            if self.source_stage is not RasterStage.BINARY:
                raise DomainValidationError("threshold boundary requires a binary source")
            if self.backend != "fourier-sketch/numpy":
                raise DomainValidationError("threshold boundary backend provenance is invalid")
        elif self.algorithm is EdgeAlgorithm.CANNY:
            if not isinstance(self.parameters, CannyParameters):
                raise DomainValidationError("Canny parameters are required")
            if self.source_stage is not RasterStage.GRAYSCALE:
                raise DomainValidationError("Canny requires a grayscale source")
            if not self.backend.startswith("opencv/") or not _safe_backend_version(
                self.backend.removeprefix("opencv/")
            ):
                raise DomainValidationError("Canny backend provenance is invalid")

    @property
    def edge_pixel_count(self) -> int:
        return self.edges.pixels.count(255)

    @property
    def is_empty(self) -> bool:
        return self.edge_pixel_count == 0


def _validate_dimensions(value: tuple[int, int]) -> None:
    if (
        not isinstance(value, tuple)
        or len(value) != 2
        or any(type(component) is not int or component < 1 for component in value)
    ):
        raise DomainValidationError("edge source dimensions must be positive integers")
    if value[0] * value[1] > MAX_DECODED_IMAGE_PIXELS:
        raise DomainValidationError("edge source dimensions exceed the pixel budget")


def _safe_backend_version(value: str) -> bool:
    return (
        1 <= len(value) <= 64
        and value[0] in _SAFE_BACKEND_CHARACTERS
        and all(character in _SAFE_BACKEND_CHARACTERS for character in value)
    )
