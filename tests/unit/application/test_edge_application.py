"""Application dispatch contracts for FS-011 edge selection."""

import pytest

from fourier_sketch.application import detect_preprocessed_edges
from fourier_sketch.domain import DomainValidationError
from fourier_sketch.imaging import (
    EdgeAlgorithm,
    ImageDecodeProvenance,
    ImageFormat,
    ImagePreprocessingProvenance,
    ImagePreprocessingResult,
    RasterImage,
    RasterStage,
)

pytestmark = pytest.mark.unit


def preprocessing_result() -> ImagePreprocessingResult:
    grayscale = RasterImage(3, 3, bytes((0, 0, 0, 0, 255, 0, 0, 0, 0)), RasterStage.GRAYSCALE)
    binary = RasterImage(3, 3, bytes((0, 0, 0, 0, 255, 0, 0, 0, 0)), RasterStage.BINARY)
    return ImagePreprocessingResult(
        grayscale,
        binary,
        ImagePreprocessingProvenance(
            ImageDecodeProvenance(ImageFormat.PNG, 10, (3, 3), (3, 3), None, False),
            ("grayscale", "threshold:128"),
        ),
    )


def test_application_selects_algorithm_specific_preprocessing_stage() -> None:
    source = preprocessing_result()

    threshold = detect_preprocessed_edges(source, EdgeAlgorithm.THRESHOLD_BOUNDARY)
    canny = detect_preprocessed_edges(source, EdgeAlgorithm.CANNY)

    assert threshold.source_stage is RasterStage.BINARY
    assert canny.source_stage is RasterStage.GRAYSCALE


def test_application_requires_typed_source_and_algorithm() -> None:
    source = preprocessing_result()
    with pytest.raises(DomainValidationError, match="preprocessing result"):
        detect_preprocessed_edges(object(), EdgeAlgorithm.CANNY)  # type: ignore[arg-type]
    with pytest.raises(DomainValidationError, match="algorithm"):
        detect_preprocessed_edges(source, "canny")  # type: ignore[arg-type]
