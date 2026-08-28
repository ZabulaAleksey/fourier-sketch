"""Real Pillow → application → typed intermediate FS-010 integration."""

from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from fourier_sketch.application import export_preprocessing_result, preprocess_local_image
from fourier_sketch.imaging import (
    DenoiseMode,
    ImageFailureCode,
    ImageFormat,
    ImageInputError,
    ImagePreprocessingOptions,
    RasterStage,
)

pytestmark = pytest.mark.integration


def test_png_runs_through_each_selected_transform_and_export(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    image = Image.new("L", (4, 3))
    image.putdata((0, 20, 40, 60, 80, 100, 120, 140, 160, 180, 220, 255))
    image.save(source)

    result = preprocess_local_image(
        source,
        ImagePreprocessingOptions(
            denoise=DenoiseMode.MEDIAN_3,
            autocontrast=True,
            threshold=128,
            invert=True,
        ),
    )
    output = tmp_path / "binary.png"
    export_preprocessing_result(result, RasterStage.BINARY, output)

    assert result.provenance.decode.source_format is ImageFormat.PNG
    assert result.provenance.transforms == (
        "grayscale",
        "median_3",
        "autocontrast",
        "threshold:128",
        "invert_binary",
    )
    assert set(result.binary.pixels) <= {0, 255}
    with Image.open(output) as exported:
        assert exported.format == "PNG"
        assert exported.mode == "L"
        assert exported.size == (4, 3)


def test_actual_format_wins_over_spoofed_extension(tmp_path: Path) -> None:
    jpeg_named_png = tmp_path / "camera.png"
    Image.new("RGB", (2, 2), "red").save(jpeg_named_png, format="JPEG")

    result = preprocess_local_image(jpeg_named_png)

    assert result.provenance.decode.source_format is ImageFormat.JPEG


def test_unsupported_content_is_rejected_even_with_png_extension(tmp_path: Path) -> None:
    tiff_named_png = tmp_path / "spoofed.png"
    Image.new("RGB", (2, 2), "red").save(tiff_named_png, format="TIFF")

    with pytest.raises(ImageInputError) as captured:
        preprocess_local_image(tiff_named_png)

    assert captured.value.code is ImageFailureCode.UNSUPPORTED_FORMAT


def test_exif_orientation_is_applied_before_grayscale(tmp_path: Path) -> None:
    source = tmp_path / "oriented.jpg"
    exif = Image.Exif()
    exif[274] = 6
    Image.new("RGB", (3, 2), "blue").save(source, format="JPEG", exif=exif)

    result = preprocess_local_image(source)

    assert result.provenance.decode.source_dimensions == (3, 2)
    assert result.provenance.decode.oriented_dimensions == (2, 3)
    assert result.provenance.decode.exif_orientation == 6
    assert result.provenance.decode.orientation_applied is True
    assert result.provenance.transforms[0] == "exif_transpose"
    assert (result.grayscale.width, result.grayscale.height) == (2, 3)


def test_decoded_pixel_limit_rejects_real_header_before_materialization(tmp_path: Path) -> None:
    source = tmp_path / "too-many-pixels.png"
    large_but_compact = Image.new("1", (6325, 6325), 0)
    large_but_compact.save(source, format="PNG")

    with pytest.raises(ImageInputError) as captured:
        preprocess_local_image(source)

    assert captured.value.code is ImageFailureCode.DECODED_LIMIT


def test_truncated_png_is_rejected_without_partial_result(tmp_path: Path) -> None:
    complete = BytesIO()
    Image.new("L", (32, 32), 128).save(complete, format="PNG")
    source = tmp_path / "truncated.png"
    source.write_bytes(complete.getvalue()[:-8])

    with pytest.raises(ImageInputError) as captured:
        preprocess_local_image(source)

    assert captured.value.code is ImageFailureCode.CORRUPT_INPUT
