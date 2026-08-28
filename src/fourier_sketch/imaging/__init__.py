"""Typed raster contracts and explicit image backend adapters."""

from .model import (
    MAX_DECODED_IMAGE_PIXELS,
    MAX_ENCODED_IMAGE_BYTES,
    DecodedImage,
    DenoiseMode,
    ImageDecodeProvenance,
    ImageFailureCode,
    ImageFormat,
    ImageInputError,
    ImagePreprocessingOptions,
    ImagePreprocessingProvenance,
    ImagePreprocessingResult,
    RasterImage,
    RasterStage,
)
from .pillow_backend import (
    autocontrast_grayscale,
    decode_image_bytes,
    decode_local_image,
    export_raster_png,
    median_denoise,
    threshold_grayscale,
)

__all__ = [
    "MAX_DECODED_IMAGE_PIXELS",
    "MAX_ENCODED_IMAGE_BYTES",
    "DecodedImage",
    "DenoiseMode",
    "ImageDecodeProvenance",
    "ImageFailureCode",
    "ImageFormat",
    "ImageInputError",
    "ImagePreprocessingOptions",
    "ImagePreprocessingProvenance",
    "ImagePreprocessingResult",
    "RasterImage",
    "RasterStage",
    "autocontrast_grayscale",
    "decode_image_bytes",
    "decode_local_image",
    "export_raster_png",
    "median_denoise",
    "threshold_grayscale",
]
