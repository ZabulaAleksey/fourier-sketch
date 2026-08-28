"""Fail-fast FS-012 application option validation."""

import pytest

from fourier_sketch.application import build_dominant_contour_timeline
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


def _blank_preprocessing() -> ImagePreprocessingResult:
    return ImagePreprocessingResult(
        grayscale=RasterImage(2, 2, bytes(4), RasterStage.GRAYSCALE),
        binary=RasterImage(2, 2, bytes(4), RasterStage.BINARY),
        provenance=ImagePreprocessingProvenance(
            decode=ImageDecodeProvenance(
                source_format=ImageFormat.PNG,
                encoded_bytes=8,
                source_dimensions=(2, 2),
                oriented_dimensions=(2, 2),
                exif_orientation=None,
                orientation_applied=False,
            ),
            transforms=("grayscale", "threshold:128"),
        ),
    )


@pytest.mark.parametrize("speed", (0.0, float("nan"), 101.0, True))
def test_invalid_speed_fails_before_edge_extraction(
    speed: float,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "fourier_sketch.application.dominant_contour.detect_preprocessed_edges",
        lambda *_args, **_kwargs: pytest.fail("edge extraction must not start"),
    )

    with pytest.raises(DomainValidationError):
        build_dominant_contour_timeline(
            _blank_preprocessing(),
            EdgeAlgorithm.THRESHOLD_BOUNDARY,
            speed=speed,
        )
