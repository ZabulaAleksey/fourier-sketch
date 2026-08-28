"""Unit validation at the FS-010 application orchestration boundary."""

from typing import cast

import pytest

from fourier_sketch.application import preprocess_local_image, select_preprocessing_raster
from fourier_sketch.imaging import (
    ImageFailureCode,
    ImageInputError,
    ImagePreprocessingOptions,
    ImagePreprocessingProvenance,
    ImagePreprocessingResult,
    RasterImage,
    RasterStage,
)

pytestmark = pytest.mark.unit


def minimal_result() -> ImagePreprocessingResult:
    from fourier_sketch.imaging import ImageDecodeProvenance, ImageFormat

    grayscale = RasterImage(1, 1, b"\x80", RasterStage.GRAYSCALE)
    binary = RasterImage(1, 1, b"\xff", RasterStage.BINARY)
    return ImagePreprocessingResult(
        grayscale,
        binary,
        ImagePreprocessingProvenance(
            ImageDecodeProvenance(ImageFormat.PNG, 1, (1, 1), (1, 1), None, False),
            ("grayscale", "threshold:128"),
        ),
    )


def test_application_rejects_non_options_before_file_access() -> None:
    with pytest.raises(ImageInputError) as captured:
        preprocess_local_image("does-not-matter.png", cast(ImagePreprocessingOptions, object()))

    assert captured.value.code is ImageFailureCode.INVALID_OPTIONS


def test_intermediate_selection_requires_explicit_stage() -> None:
    with pytest.raises(ImageInputError) as captured:
        select_preprocessing_raster(minimal_result(), cast(RasterStage, "edge"))

    assert captured.value.code is ImageFailureCode.INVALID_OPTIONS
