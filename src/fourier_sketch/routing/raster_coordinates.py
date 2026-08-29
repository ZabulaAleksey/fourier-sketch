"""Shared, deterministic raster-to-domain coordinate transform."""

from dataclasses import dataclass
from math import isfinite

from fourier_sketch.domain import DomainValidationError, Point2D
from fourier_sketch.imaging.contour_model import PixelPoint

COORDINATE_TRANSFORM_ID = "pixel-center-centered-aspect-v1"


@dataclass(frozen=True, slots=True)
class RasterCoordinateTransform:
    """Map pixel centres to a centred, aspect-preserving domain."""

    dimensions: tuple[int, int]
    scale: float

    def __post_init__(self) -> None:
        if (
            not isinstance(self.dimensions, tuple)
            or len(self.dimensions) != 2
            or any(type(value) is not int or value < 1 for value in self.dimensions)
        ):
            raise DomainValidationError("raster dimensions must be positive integers")
        if (
            type(self.scale) is not float
            or not isfinite(self.scale)
            or self.scale <= 0.0
        ):
            raise DomainValidationError("raster scale must be finite and positive")

    @classmethod
    def for_dimensions(cls, dimensions: tuple[int, int]) -> "RasterCoordinateTransform":
        if (
            not isinstance(dimensions, tuple)
            or len(dimensions) != 2
            or any(type(value) is not int or value < 1 for value in dimensions)
        ):
            raise DomainValidationError("raster dimensions must be positive integers")
        width, height = dimensions
        span = max(width - 1, height - 1)
        return cls(dimensions, 1.0 if span == 0 else 2.0 / span)

    def point(self, pixel: PixelPoint) -> Point2D:
        width, height = self.dimensions
        if not isinstance(pixel, PixelPoint) or pixel.column >= width or pixel.row >= height:
            raise DomainValidationError("pixel is outside raster dimensions")
        return Point2D(
            (pixel.column - (width - 1) / 2.0) * self.scale,
            ((height - 1) / 2.0 - pixel.row) * self.scale,
        )

    def points(self, pixels: tuple[PixelPoint, ...]) -> tuple[Point2D, ...]:
        if not isinstance(pixels, tuple) or any(
            not isinstance(pixel, PixelPoint) for pixel in pixels
        ):
            raise DomainValidationError("raster pixels must be an immutable typed tuple")
        return tuple(self.point(pixel) for pixel in pixels)
