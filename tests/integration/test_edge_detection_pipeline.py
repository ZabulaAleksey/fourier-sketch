"""Real FS-010 preprocessing -> FS-011 algorithm -> PNG integration."""

from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from fourier_sketch.application import (
    detect_preprocessed_edges,
    export_edge_result,
    preprocess_local_image,
)
from fourier_sketch.imaging import CannyParameters, EdgeAlgorithm, ImagePreprocessingOptions

pytestmark = pytest.mark.integration


def test_real_image_runs_through_both_non_equivalent_edge_algorithms(tmp_path: Path) -> None:
    source = tmp_path / "shape.png"
    image = Image.new("L", (32, 24), 0)
    ImageDraw.Draw(image).rectangle((7, 5, 24, 18), fill=255)
    image.save(source)
    preprocessing = preprocess_local_image(source, ImagePreprocessingOptions(threshold=128))

    threshold = detect_preprocessed_edges(preprocessing, EdgeAlgorithm.THRESHOLD_BOUNDARY)
    canny = detect_preprocessed_edges(
        preprocessing,
        EdgeAlgorithm.CANNY,
        canny_parameters=CannyParameters(50, 150, 3, True),
    )

    assert threshold.backend == "fourier-sketch/numpy"
    assert canny.backend.startswith("opencv/")
    assert threshold.edges.pixels != canny.edges.pixels
    assert threshold.edge_pixel_count > 0
    assert canny.edge_pixel_count > 0


def test_selected_edge_intermediate_exports_as_binary_png(tmp_path: Path) -> None:
    source = tmp_path / "shape.png"
    output = tmp_path / "edges.png"
    Image.new("L", (8, 6), 255).save(source)
    preprocessing = preprocess_local_image(source)
    result = detect_preprocessed_edges(preprocessing, EdgeAlgorithm.THRESHOLD_BOUNDARY)

    export_edge_result(result, output)

    with Image.open(output) as exported:
        assert exported.mode == "L"
        assert exported.size == (8, 6)
        assert set(exported.get_flattened_data()) <= {0, 255}
