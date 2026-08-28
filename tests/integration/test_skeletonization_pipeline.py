"""Real preprocessing and scikit-image Lee integration for FS-014."""

from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw

from fourier_sketch.application import SkeletonConfig, build_local_skeleton
from fourier_sketch.imaging import ImagePreprocessingOptions

pytestmark = pytest.mark.integration


def _write_fixture(path: Path, kind: str, *, image_format: str = "PNG") -> None:
    image = Image.new("L", (41, 41), 0)
    draw = ImageDraw.Draw(image)
    if kind == "line":
        draw.line((6, 20, 34, 20), fill=255, width=7)
    elif kind == "t":
        draw.line((6, 9, 34, 9), fill=255, width=7)
        draw.line((20, 9, 20, 34), fill=255, width=7)
    elif kind == "cross":
        draw.line((5, 20, 35, 20), fill=255, width=7)
        draw.line((20, 5, 20, 35), fill=255, width=7)
    elif kind == "loop":
        draw.rectangle((7, 7, 33, 33), outline=255, width=7)
    elif kind == "noise":
        draw.line((6, 20, 34, 20), fill=255, width=7)
        draw.point((3, 3), fill=255)
        draw.point((37, 35), fill=255)
    else:
        raise AssertionError(kind)
    image.save(path, format=image_format, quality=100)


@pytest.mark.parametrize("kind", ("line", "t", "cross", "loop", "noise"))
def test_real_lee_fixtures_are_thinned_without_mutating_source(
    kind: str,
    tmp_path: Path,
) -> None:
    source_path = tmp_path / f"{kind}.png"
    _write_fixture(source_path, kind)

    result = build_local_skeleton(
        source_path,
        SkeletonConfig(preprocessing=ImagePreprocessingOptions(threshold=128)),
    )

    source = result.preprocessing.binary
    skeleton = result.skeletonization
    assert skeleton.backend == "scikit-image/0.26.0"
    assert skeleton.source == source
    assert skeleton.source_dimensions == (41, 41)
    assert 0 < skeleton.skeleton_pixel_count < skeleton.source_foreground_pixels
    assert all(
        output == 0 or source_pixel == 255
        for output, source_pixel in zip(
            skeleton.skeleton.pixels,
            source.pixels,
            strict=True,
        )
    )
    values = np.frombuffer(skeleton.skeleton.pixels, dtype=np.uint8).reshape(41, 41) == 255
    solid_two_by_two = values[:-1, :-1] & values[1:, :-1] & values[:-1, 1:] & values[1:, 1:]
    assert not solid_two_by_two.any()


def test_real_jpeg_reaches_same_sized_binary_skeleton(tmp_path: Path) -> None:
    source_path = tmp_path / "line.jpg"
    _write_fixture(source_path, "line", image_format="JPEG")

    result = build_local_skeleton(source_path)

    assert result.preprocessing.provenance.decode.source_format.value == "JPEG"
    assert result.skeletonization.skeleton.width == 41
    assert result.skeletonization.skeleton.height == 41
    assert result.skeletonization.skeleton_pixel_count > 0


def test_empty_binary_is_a_successful_empty_skeleton(tmp_path: Path) -> None:
    source_path = tmp_path / "empty.png"
    Image.new("L", (12, 9), 0).save(source_path)

    result = build_local_skeleton(source_path)

    assert result.skeletonization.is_empty
    assert result.skeletonization.source_foreground_pixels == 0
    assert result.skeletonization.skeleton.pixels == bytes(12 * 9)
