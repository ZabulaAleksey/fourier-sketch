"""Pillow-neutral raster contracts for the local image preprocessing stages."""

from dataclasses import dataclass
from enum import StrEnum

from fourier_sketch.domain import DomainValidationError

MAX_ENCODED_IMAGE_BYTES = 25 * 1024 * 1024
MAX_DECODED_IMAGE_PIXELS = 40_000_000


class ImageFormat(StrEnum):
    """Actually decoded input formats accepted by the project."""

    PNG = "PNG"
    JPEG = "JPEG"


class RasterStage(StrEnum):
    """Semantics of the bytes stored by a raster value."""

    GRAYSCALE = "grayscale"
    BINARY = "binary"


class DenoiseMode(StrEnum):
    """Bounded preprocessing choices available in FS-010."""

    NONE = "none"
    MEDIAN_3 = "median_3"


class ImageFailureCode(StrEnum):
    """Stable failure categories that do not expose paths or payloads."""

    INVALID_PATH = "invalid_path"
    EMPTY_INPUT = "empty_input"
    ENCODED_LIMIT = "encoded_limit"
    DECODED_LIMIT = "decoded_limit"
    UNSUPPORTED_FORMAT = "unsupported_format"
    CORRUPT_INPUT = "corrupt_input"
    MULTIFRAME_INPUT = "multiframe_input"
    INVALID_OPTIONS = "invalid_options"


class ImageInputError(DomainValidationError):
    """Typed fail-closed image error with privacy-safe public context."""

    def __init__(self, code: ImageFailureCode, message: str) -> None:
        if not isinstance(code, ImageFailureCode) or not isinstance(message, str) or not message:
            raise DomainValidationError("image error requires a typed code and message")
        self.code = code
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class RasterImage:
    """Immutable one-byte-per-pixel raster independent of Pillow and NumPy."""

    width: int
    height: int
    pixels: bytes
    stage: RasterStage

    def __post_init__(self) -> None:
        if type(self.width) is not int or type(self.height) is not int:
            raise DomainValidationError("raster dimensions must be integers")
        if self.width < 1 or self.height < 1:
            raise DomainValidationError("raster dimensions must be positive")
        pixel_count = self.width * self.height
        if pixel_count > MAX_DECODED_IMAGE_PIXELS:
            raise DomainValidationError("raster exceeds decoded pixel limit")
        if not isinstance(self.pixels, bytes) or len(self.pixels) != pixel_count:
            raise DomainValidationError("raster payload size must match dimensions")
        if not isinstance(self.stage, RasterStage):
            raise DomainValidationError("raster stage must be explicit")
        if self.stage is RasterStage.BINARY and any(value not in (0, 255) for value in self.pixels):
            raise DomainValidationError("binary raster pixels must be 0 or 255")

    @property
    def pixel_count(self) -> int:
        return self.width * self.height


@dataclass(frozen=True, slots=True)
class ImageDecodeProvenance:
    """Observable decode decisions without source path or metadata payload."""

    source_format: ImageFormat
    encoded_bytes: int
    source_dimensions: tuple[int, int]
    oriented_dimensions: tuple[int, int]
    exif_orientation: int | None
    orientation_applied: bool

    def __post_init__(self) -> None:
        if not isinstance(self.source_format, ImageFormat):
            raise DomainValidationError("source format must be explicit")
        if (
            type(self.encoded_bytes) is not int
            or not 1 <= self.encoded_bytes <= MAX_ENCODED_IMAGE_BYTES
        ):
            raise DomainValidationError("encoded byte count is outside the accepted budget")
        _validate_dimensions(self.source_dimensions, "source")
        _validate_dimensions(self.oriented_dimensions, "oriented")
        if self.source_dimensions[0] * self.source_dimensions[1] != (
            self.oriented_dimensions[0] * self.oriented_dimensions[1]
        ):
            raise DomainValidationError("orientation must preserve pixel count")
        if self.exif_orientation is not None and (
            type(self.exif_orientation) is not int or not 1 <= self.exif_orientation <= 8
        ):
            raise DomainValidationError("EXIF orientation must be between 1 and 8")
        if type(self.orientation_applied) is not bool:
            raise DomainValidationError("orientation_applied must be boolean")
        expected_applied = self.exif_orientation is not None and self.exif_orientation != 1
        if self.orientation_applied is not expected_applied:
            raise DomainValidationError("orientation decision must match EXIF provenance")
        expected_dimensions = self.source_dimensions
        if self.exif_orientation in (5, 6, 7, 8):
            expected_dimensions = (self.source_dimensions[1], self.source_dimensions[0])
        if self.oriented_dimensions != expected_dimensions:
            raise DomainValidationError("oriented dimensions must match EXIF orientation")


@dataclass(frozen=True, slots=True)
class DecodedImage:
    """Decoded and oriented grayscale raster returned by the Pillow adapter."""

    grayscale: RasterImage
    provenance: ImageDecodeProvenance

    def __post_init__(self) -> None:
        if not isinstance(self.grayscale, RasterImage) or not isinstance(
            self.provenance, ImageDecodeProvenance
        ):
            raise DomainValidationError("decoded image values must use typed contracts")
        if self.grayscale.stage is not RasterStage.GRAYSCALE:
            raise DomainValidationError("decoded image must contain grayscale pixels")
        if (self.grayscale.width, self.grayscale.height) != self.provenance.oriented_dimensions:
            raise DomainValidationError("decoded raster dimensions must match provenance")


@dataclass(frozen=True, slots=True)
class ImagePreprocessingOptions:
    """Explicit deterministic transform selection for FS-010."""

    denoise: DenoiseMode = DenoiseMode.NONE
    autocontrast: bool = False
    threshold: int = 128
    invert: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.denoise, DenoiseMode):
            raise ImageInputError(ImageFailureCode.INVALID_OPTIONS, "denoise mode is invalid")
        if type(self.autocontrast) is not bool or type(self.invert) is not bool:
            raise ImageInputError(ImageFailureCode.INVALID_OPTIONS, "image flags must be boolean")
        if type(self.threshold) is not int or not 0 <= self.threshold <= 255:
            raise ImageInputError(
                ImageFailureCode.INVALID_OPTIONS,
                "threshold must be an integer between 0 and 255",
            )


@dataclass(frozen=True, slots=True)
class ImagePreprocessingProvenance:
    """Ordered transform record built by the application use case."""

    decode: ImageDecodeProvenance
    transforms: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.decode, ImageDecodeProvenance):
            raise DomainValidationError("preprocessing provenance requires decode provenance")
        if (
            not isinstance(self.transforms, tuple)
            or not self.transforms
            or any(not isinstance(value, str) or not value for value in self.transforms)
        ):
            raise DomainValidationError("preprocessing transforms must be recorded")


@dataclass(frozen=True, slots=True)
class ImagePreprocessingResult:
    """Both FS-010 intermediate outputs with shared provenance."""

    grayscale: RasterImage
    binary: RasterImage
    provenance: ImagePreprocessingProvenance

    def __post_init__(self) -> None:
        if (
            not isinstance(self.grayscale, RasterImage)
            or not isinstance(self.binary, RasterImage)
            or not isinstance(self.provenance, ImagePreprocessingProvenance)
        ):
            raise DomainValidationError("preprocessing result values must use typed contracts")
        if self.grayscale.stage is not RasterStage.GRAYSCALE:
            raise DomainValidationError("grayscale result has an invalid stage")
        if self.binary.stage is not RasterStage.BINARY:
            raise DomainValidationError("binary result has an invalid stage")
        if (self.grayscale.width, self.grayscale.height) != (
            self.binary.width,
            self.binary.height,
        ):
            raise DomainValidationError("preprocessing intermediates must share dimensions")
        if (self.grayscale.width, self.grayscale.height) != (
            self.provenance.decode.oriented_dimensions
        ):
            raise DomainValidationError("result dimensions must match decode provenance")


def _validate_dimensions(value: tuple[int, int], field_name: str) -> None:
    if (
        not isinstance(value, tuple)
        or len(value) != 2
        or any(type(component) is not int or component < 1 for component in value)
    ):
        raise DomainValidationError(f"{field_name} dimensions must be positive integers")
    if value[0] * value[1] > MAX_DECODED_IMAGE_PIXELS:
        raise DomainValidationError(f"{field_name} dimensions exceed decoded pixel limit")
