"""Unit and negative contracts for the bounded Pillow adapter."""

from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from fourier_sketch.imaging import (
    MAX_ENCODED_IMAGE_BYTES,
    ImageFailureCode,
    ImageFormat,
    ImageInputError,
    RasterImage,
    RasterStage,
    autocontrast_grayscale,
    decode_image_bytes,
    decode_local_image,
    export_raster_png,
    median_denoise,
    threshold_grayscale,
)

pytestmark = pytest.mark.unit


def encoded_image(
    image_format: str,
    *,
    size: tuple[int, int] = (3, 2),
    mode: str = "RGB",
) -> bytes:
    output = BytesIO()
    Image.new(mode, size, "white").save(output, format=image_format)
    return output.getvalue()


@pytest.mark.parametrize(
    ("image_format", "expected"),
    (("PNG", ImageFormat.PNG), ("JPEG", ImageFormat.JPEG)),
)
def test_decoder_accepts_only_actual_allowlisted_formats(
    image_format: str,
    expected: ImageFormat,
) -> None:
    decoded = decode_image_bytes(encoded_image(image_format))

    assert decoded.provenance.source_format is expected
    assert decoded.grayscale.stage is RasterStage.GRAYSCALE
    assert decoded.grayscale.pixel_count == 6


def test_decoder_rejects_unsupported_actual_format() -> None:
    with pytest.raises(ImageInputError) as captured:
        decode_image_bytes(encoded_image("TIFF"))

    assert captured.value.code is ImageFailureCode.UNSUPPORTED_FORMAT


@pytest.mark.parametrize("payload", (b"", b"not an image", b"\x89PNG\r\n\x1a\n"))
def test_decoder_rejects_empty_or_corrupt_payload(payload: bytes) -> None:
    with pytest.raises(ImageInputError) as captured:
        decode_image_bytes(payload)

    assert captured.value.code in {
        ImageFailureCode.EMPTY_INPUT,
        ImageFailureCode.UNSUPPORTED_FORMAT,
    }


def test_decoder_rejects_multiframe_png() -> None:
    output = BytesIO()
    first = Image.new("L", (2, 2), 0)
    second = Image.new("L", (2, 2), 255)
    first.save(output, format="PNG", save_all=True, append_images=[second], duration=10, loop=0)

    with pytest.raises(ImageInputError) as captured:
        decode_image_bytes(output.getvalue())

    assert captured.value.code is ImageFailureCode.MULTIFRAME_INPUT


def test_encoded_file_limit_is_checked_before_decode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "oversized.png"
    with source.open("wb") as stream:
        stream.seek(MAX_ENCODED_IMAGE_BYTES)
        stream.write(b"x")
    called = False

    def fail_if_called(payload: bytes) -> None:
        nonlocal called
        called = True

    monkeypatch.setattr("fourier_sketch.imaging.pillow_backend.decode_image_bytes", fail_if_called)

    with pytest.raises(ImageInputError) as captured:
        decode_local_image(source)

    assert captured.value.code is ImageFailureCode.ENCODED_LIMIT
    assert called is False


def test_individual_grayscale_transforms_are_deterministic() -> None:
    line = RasterImage(4, 1, bytes((50, 75, 100, 125)), RasterStage.GRAYSCALE)
    contrasted = autocontrast_grayscale(line)
    thresholded = threshold_grayscale(line, threshold=100)
    inverted = threshold_grayscale(line, threshold=100, invert=True)

    assert contrasted.pixels == bytes((0, 85, 170, 255))
    assert thresholded.pixels == bytes((0, 0, 255, 255))
    assert inverted.pixels == bytes((255, 255, 0, 0))


def test_fixed_median_filter_removes_single_pixel_impulse() -> None:
    impulse = RasterImage(3, 3, bytes((0, 0, 0, 0, 255, 0, 0, 0, 0)), RasterStage.GRAYSCALE)

    assert median_denoise(impulse).pixels == bytes(9)


def test_png_export_does_not_overwrite_without_explicit_choice(tmp_path: Path) -> None:
    raster = RasterImage(1, 1, b"\xff", RasterStage.GRAYSCALE)
    destination = tmp_path / "result.png"
    destination.write_bytes(b"user data")

    with pytest.raises(FileExistsError):
        export_raster_png(raster, destination)

    assert destination.read_bytes() == b"user data"
    export_raster_png(raster, destination, overwrite=True)
    assert destination.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_png_export_cleans_temporary_file_when_publication_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raster = RasterImage(1, 1, b"\xff", RasterStage.GRAYSCALE)
    destination = tmp_path / "result.png"

    def fail_link(source: Path, target: Path) -> None:
        _ = (source, target)
        raise OSError("simulated publication failure")

    monkeypatch.setattr("fourier_sketch.imaging.pillow_backend.os.link", fail_link)

    with pytest.raises(OSError, match="publication failure"):
        export_raster_png(raster, destination)

    assert not destination.exists()
    assert tuple(tmp_path.glob(".*.tmp")) == ()
