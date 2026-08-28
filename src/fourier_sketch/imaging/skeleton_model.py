"""Typed contracts for the FS-014 skeletonization boundary."""

from dataclasses import dataclass
from enum import StrEnum

from fourier_sketch.domain import DomainValidationError

from .model import RasterImage, RasterStage

MAX_SKELETON_FOREGROUND_PIXELS = 4_000_000
_SAFE = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._+-")


class SkeletonAlgorithm(StrEnum):
    LEE = "lee"


class SkeletonFailureCode(StrEnum):
    INVALID_INPUT = "invalid_input"
    RESOURCE_LIMIT = "resource_limit"
    BACKEND_UNAVAILABLE = "backend_unavailable"
    BACKEND_FAILURE = "backend_failure"
    MALFORMED_OUTPUT = "malformed_output"
    CANCELLED = "cancelled"


class SkeletonizationError(DomainValidationError):
    def __init__(self, code: SkeletonFailureCode, message: str) -> None:
        if not isinstance(code, SkeletonFailureCode) or not isinstance(message, str) or not message:
            raise DomainValidationError("skeleton error requires a typed code and message")
        self.code = code
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class SkeletonizationResult:
    source: RasterImage
    skeleton: RasterImage
    algorithm: SkeletonAlgorithm
    backend: str
    source_dimensions: tuple[int, int]
    source_foreground_pixels: int
    skeleton_foreground_pixels: int

    def __post_init__(self) -> None:
        if not isinstance(self.source, RasterImage) or self.source.stage is not RasterStage.BINARY:
            raise DomainValidationError("skeleton source must be a binary raster")
        if (
            not isinstance(self.skeleton, RasterImage)
            or self.skeleton.stage is not RasterStage.BINARY
        ):
            raise DomainValidationError("skeleton must be a binary raster")
        if not isinstance(self.algorithm, SkeletonAlgorithm):
            raise DomainValidationError("skeleton algorithm must be explicit")
        if not _safe_backend(self.backend) or not self.backend.startswith("scikit-image/"):
            raise DomainValidationError("skeleton backend provenance is invalid")
        dimensions = (self.source.width, self.source.height)
        if (
            self.source_dimensions != dimensions
            or (self.skeleton.width, self.skeleton.height) != dimensions
        ):
            raise DomainValidationError("skeleton dimensions must match source")
        source_count = self.source.pixels.count(255)
        skeleton_count = self.skeleton.pixels.count(255)
        if (
            self.source_foreground_pixels != source_count
            or self.skeleton_foreground_pixels != skeleton_count
        ):
            raise DomainValidationError("skeleton pixel counts do not match rasters")
        if any(
            value == 255 and source == 0
            for value, source in zip(self.skeleton.pixels, self.source.pixels, strict=True)
        ):
            raise DomainValidationError("skeleton foreground must be a subset of source foreground")
        if _has_solid_two_by_two(self.skeleton):
            raise DomainValidationError(
                "skeleton cannot contain a solid two-by-two foreground block"
            )

    @property
    def is_empty(self) -> bool:
        return self.skeleton_foreground_pixels == 0

    @property
    def skeleton_pixel_count(self) -> int:
        return self.skeleton_foreground_pixels


def _safe_backend(value: str) -> bool:
    if not isinstance(value, str) or not value.startswith("scikit-image/"):
        return False
    version = value.removeprefix("scikit-image/")
    return 1 <= len(version) <= 32 and all(character in _SAFE for character in version)


def _has_solid_two_by_two(raster: RasterImage) -> bool:
    for row in range(raster.height - 1):
        offset = row * raster.width
        next_offset = offset + raster.width
        for column in range(raster.width - 1):
            if (
                raster.pixels[offset + column] == 255
                and raster.pixels[offset + column + 1] == 255
                and raster.pixels[next_offset + column] == 255
                and raster.pixels[next_offset + column + 1] == 255
            ):
                return True
    return False
