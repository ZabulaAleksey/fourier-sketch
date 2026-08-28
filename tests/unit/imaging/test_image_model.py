"""Unit contracts for Pillow-neutral FS-010 raster values."""

import pytest

from fourier_sketch.domain import DomainValidationError
from fourier_sketch.imaging import (
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

pytestmark = pytest.mark.unit


def test_grayscale_raster_is_immutable_and_dimension_checked() -> None:
    raster = RasterImage(2, 2, bytes((0, 64, 128, 255)), RasterStage.GRAYSCALE)

    assert raster.pixel_count == 4
    with pytest.raises(DomainValidationError, match="payload size"):
        RasterImage(2, 2, b"short", RasterStage.GRAYSCALE)


def test_binary_raster_rejects_non_binary_values() -> None:
    with pytest.raises(DomainValidationError, match="0 or 255"):
        RasterImage(2, 1, bytes((0, 1)), RasterStage.BINARY)


@pytest.mark.parametrize("threshold", (-1, 256, 1.5, True))
def test_preprocessing_options_reject_invalid_threshold(threshold: object) -> None:
    with pytest.raises(ImageInputError) as captured:
        ImagePreprocessingOptions(threshold=threshold)  # type: ignore[arg-type]

    assert captured.value.code is ImageFailureCode.INVALID_OPTIONS


def test_preprocessing_options_require_explicit_denoise_enum() -> None:
    with pytest.raises(ImageInputError) as captured:
        ImagePreprocessingOptions(denoise="median_3")  # type: ignore[arg-type]

    assert captured.value.code is ImageFailureCode.INVALID_OPTIONS
    assert ImagePreprocessingOptions(denoise=DenoiseMode.MEDIAN_3).denoise is DenoiseMode.MEDIAN_3


def decode_provenance(
    *,
    source: tuple[int, int] = (2, 1),
    oriented: tuple[int, int] = (2, 1),
    orientation: int | None = None,
    applied: bool = False,
) -> ImageDecodeProvenance:
    return ImageDecodeProvenance(
        ImageFormat.PNG,
        10,
        source,
        oriented,
        orientation,
        applied,
    )


@pytest.mark.parametrize(
    ("source", "oriented", "orientation", "applied"),
    (
        ((2, 1), (1, 2), None, False),
        ((2, 1), (2, 1), 6, True),
        ((2, 1), (1, 2), 1, True),
        ((2, 1), (2, 1), 3, False),
    ),
)
def test_decode_provenance_requires_coherent_exif_decision(
    source: tuple[int, int],
    oriented: tuple[int, int],
    orientation: int | None,
    applied: bool,
) -> None:
    with pytest.raises(DomainValidationError, match="orientation"):
        decode_provenance(
            source=source,
            oriented=oriented,
            orientation=orientation,
            applied=applied,
        )


def test_nested_result_contracts_reject_mutable_or_spoofed_values() -> None:
    grayscale = RasterImage(2, 1, b"\x00\xff", RasterStage.GRAYSCALE)
    binary = RasterImage(2, 1, b"\x00\xff", RasterStage.BINARY)
    decode = decode_provenance()

    with pytest.raises(DomainValidationError, match="decode provenance"):
        ImagePreprocessingProvenance(object(), ("grayscale",))  # type: ignore[arg-type]
    with pytest.raises(DomainValidationError, match="transforms"):
        ImagePreprocessingProvenance(decode, ["grayscale"])  # type: ignore[arg-type]
    with pytest.raises(DomainValidationError, match="typed contracts"):
        ImagePreprocessingResult(grayscale, binary, object())  # type: ignore[arg-type]
    with pytest.raises(DomainValidationError, match="typed contracts"):
        DecodedImage(grayscale, object())  # type: ignore[arg-type]


def test_result_dimensions_must_match_decode_provenance() -> None:
    grayscale = RasterImage(1, 2, b"\x00\xff", RasterStage.GRAYSCALE)
    binary = RasterImage(1, 2, b"\x00\xff", RasterStage.BINARY)
    provenance = ImagePreprocessingProvenance(decode_provenance(), ("grayscale",))

    with pytest.raises(DomainValidationError, match="decode provenance"):
        ImagePreprocessingResult(grayscale, binary, provenance)
