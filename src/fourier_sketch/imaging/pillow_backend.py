"""Fail-closed Pillow adapter and bounded individual image transforms."""

import os
import tempfile
import warnings
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps, UnidentifiedImageError

from .model import (
    MAX_DECODED_IMAGE_PIXELS,
    MAX_ENCODED_IMAGE_BYTES,
    DecodedImage,
    ImageDecodeProvenance,
    ImageFailureCode,
    ImageFormat,
    ImageInputError,
    RasterImage,
    RasterStage,
)

_ALLOWED_PIL_FORMATS = (ImageFormat.PNG.value, ImageFormat.JPEG.value)
_EXIF_ORIENTATION_TAG = 274


def decode_local_image(path: str | Path) -> DecodedImage:
    """Read a bounded local file and decode only allowlisted actual formats."""
    candidate = Path(path)
    try:
        stat = candidate.stat()
    except OSError as error:
        raise ImageInputError(ImageFailureCode.INVALID_PATH, "image file is unavailable") from error
    if not candidate.is_file():
        raise ImageInputError(ImageFailureCode.INVALID_PATH, "image input must be a file")
    _validate_encoded_size(stat.st_size)
    try:
        with candidate.open("rb") as stream:
            payload = stream.read(MAX_ENCODED_IMAGE_BYTES + 1)
    except OSError as error:
        raise ImageInputError(ImageFailureCode.INVALID_PATH, "image file cannot be read") from error
    _validate_encoded_size(len(payload))
    if len(payload) != stat.st_size:
        raise ImageInputError(ImageFailureCode.INVALID_PATH, "image changed while being read")
    return decode_image_bytes(payload)


def decode_image_bytes(payload: bytes) -> DecodedImage:
    """Verify, fully decode, orient and convert stable in-memory bytes to grayscale."""
    if not isinstance(payload, bytes):
        raise ImageInputError(ImageFailureCode.CORRUPT_INPUT, "image payload must be bytes")
    _validate_encoded_size(len(payload))
    source_format, source_dimensions = _verified_header(payload)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(payload), formats=_ALLOWED_PIL_FORMATS) as source:
                if _validate_open_image(source) is not source_format:
                    raise ImageInputError(
                        ImageFailureCode.CORRUPT_INPUT,
                        "image format changed between verification and decode",
                    )
                exif_orientation = _validated_exif_orientation(
                    source.getexif().get(_EXIF_ORIENTATION_TAG)
                )
                source.load()
                oriented = ImageOps.exif_transpose(source)
                oriented.load()
                oriented_dimensions = _validated_dimensions(oriented.size)
                grayscale_image = ImageOps.grayscale(oriented)
                grayscale_image.load()
                pixels = grayscale_image.tobytes()
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
        raise ImageInputError(
            ImageFailureCode.DECODED_LIMIT,
            "decoded image exceeds the pixel budget",
        ) from error
    except ImageInputError:
        raise
    except (UnidentifiedImageError, OSError, RuntimeError, SyntaxError, ValueError) as error:
        raise ImageInputError(ImageFailureCode.CORRUPT_INPUT, "image decode failed") from error

    grayscale = RasterImage(
        width=oriented_dimensions[0],
        height=oriented_dimensions[1],
        pixels=pixels,
        stage=RasterStage.GRAYSCALE,
    )
    orientation_applied = exif_orientation is not None and exif_orientation != 1
    return DecodedImage(
        grayscale=grayscale,
        provenance=ImageDecodeProvenance(
            source_format=source_format,
            encoded_bytes=len(payload),
            source_dimensions=source_dimensions,
            oriented_dimensions=oriented_dimensions,
            exif_orientation=exif_orientation,
            orientation_applied=orientation_applied,
        ),
    )


def median_denoise(raster: RasterImage) -> RasterImage:
    """Apply the only bounded FS-010 denoise mode: a fixed 3x3 median filter."""
    image = _grayscale_pillow_image(raster)
    return _grayscale_raster(image.filter(ImageFilter.MedianFilter(size=3)))


def autocontrast_grayscale(raster: RasterImage) -> RasterImage:
    """Stretch grayscale extrema using Pillow's deterministic default policy."""
    return _grayscale_raster(ImageOps.autocontrast(_grayscale_pillow_image(raster)))


def threshold_grayscale(
    raster: RasterImage,
    *,
    threshold: int,
    invert: bool = False,
) -> RasterImage:
    """Map values below/above the inclusive threshold to 0/255, optionally inverted."""
    if type(threshold) is not int or not 0 <= threshold <= 255 or type(invert) is not bool:
        raise ImageInputError(ImageFailureCode.INVALID_OPTIONS, "threshold options are invalid")
    low, high = (255, 0) if invert else (0, 255)
    lookup = [low if value < threshold else high for value in range(256)]
    binary = _grayscale_pillow_image(raster).point(lookup, mode="L")
    return RasterImage(
        width=raster.width,
        height=raster.height,
        pixels=binary.tobytes(),
        stage=RasterStage.BINARY,
    )


def export_raster_png(
    raster: RasterImage,
    destination: str | Path,
    *,
    overwrite: bool = False,
) -> None:
    """Encode before opening the destination and never overwrite implicitly."""
    if type(overwrite) is not bool:
        raise ImageInputError(ImageFailureCode.INVALID_OPTIONS, "overwrite must be boolean")
    target = Path(destination)
    if target.suffix.lower() != ".png":
        raise ImageInputError(ImageFailureCode.INVALID_OPTIONS, "diagnostic output must be PNG")
    if not target.parent.is_dir():
        raise ImageInputError(
            ImageFailureCode.INVALID_PATH,
            "diagnostic output parent is unavailable",
        )
    if target.exists() and not overwrite:
        raise FileExistsError(target.name)
    encoded = BytesIO()
    _raster_pillow_image(raster).save(encoded, format="PNG")
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{target.stem}.",
            suffix=".tmp",
            dir=target.parent,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(encoded.getvalue())
        if overwrite:
            os.replace(temporary_path, target)
            temporary_path = None
        else:
            os.link(temporary_path, target)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def _verified_header(payload: bytes) -> tuple[ImageFormat, tuple[int, int]]:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(payload), formats=_ALLOWED_PIL_FORMATS) as probe:
                source_format = _validate_open_image(probe, check_multiframe=False)
                dimensions = _validated_dimensions(probe.size)
                probe.verify()
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
        raise ImageInputError(
            ImageFailureCode.DECODED_LIMIT,
            "decoded image exceeds the pixel budget",
        ) from error
    except ImageInputError:
        raise
    except UnidentifiedImageError as error:
        raise ImageInputError(
            ImageFailureCode.UNSUPPORTED_FORMAT,
            "image format is not PNG or JPEG",
        ) from error
    except (OSError, RuntimeError, SyntaxError, ValueError) as error:
        raise ImageInputError(
            ImageFailureCode.CORRUPT_INPUT, "image verification failed"
        ) from error
    return source_format, dimensions


def _validate_open_image(image: Image.Image, *, check_multiframe: bool = True) -> ImageFormat:
    format_name = image.format
    if format_name is None:
        raise ImageInputError(
            ImageFailureCode.UNSUPPORTED_FORMAT,
            "image format is not PNG or JPEG",
        )
    try:
        source_format = ImageFormat(format_name)
    except ValueError as error:
        raise ImageInputError(
            ImageFailureCode.UNSUPPORTED_FORMAT,
            "image format is not PNG or JPEG",
        ) from error
    _validated_dimensions(image.size)
    if check_multiframe and (
        getattr(image, "n_frames", 1) != 1 or getattr(image, "is_animated", False)
    ):
        raise ImageInputError(
            ImageFailureCode.MULTIFRAME_INPUT,
            "animated or multiframe image input is not supported",
        )
    return source_format


def _validate_encoded_size(size: int) -> None:
    if size < 1:
        raise ImageInputError(ImageFailureCode.EMPTY_INPUT, "image payload is empty")
    if size > MAX_ENCODED_IMAGE_BYTES:
        raise ImageInputError(
            ImageFailureCode.ENCODED_LIMIT,
            "encoded image exceeds the byte budget",
        )


def _validated_dimensions(dimensions: tuple[int, int]) -> tuple[int, int]:
    width, height = dimensions
    if type(width) is not int or type(height) is not int or width < 1 or height < 1:
        raise ImageInputError(ImageFailureCode.CORRUPT_INPUT, "image dimensions are invalid")
    if width * height > MAX_DECODED_IMAGE_PIXELS:
        raise ImageInputError(
            ImageFailureCode.DECODED_LIMIT,
            "decoded image exceeds the pixel budget",
        )
    return width, height


def _validated_exif_orientation(value: object) -> int | None:
    if value is None:
        return None
    if type(value) is not int or not 1 <= value <= 8:
        raise ImageInputError(ImageFailureCode.CORRUPT_INPUT, "EXIF orientation is invalid")
    return value


def _grayscale_pillow_image(raster: RasterImage) -> Image.Image:
    if raster.stage is not RasterStage.GRAYSCALE:
        raise ImageInputError(
            ImageFailureCode.INVALID_OPTIONS,
            "transform requires a grayscale raster",
        )
    return _raster_pillow_image(raster)


def _raster_pillow_image(raster: RasterImage) -> Image.Image:
    return Image.frombytes("L", (raster.width, raster.height), raster.pixels)


def _grayscale_raster(image: Image.Image) -> RasterImage:
    image.load()
    return RasterImage(
        width=image.width,
        height=image.height,
        pixels=image.tobytes(),
        stage=RasterStage.GRAYSCALE,
    )
