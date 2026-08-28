"""Real image, edge, contour, Fourier and renderer integration for FS-013."""

from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from fourier_sketch.application import (
    ImageContourTimelineResult,
    ImageMvpConfig,
    ImageMvpController,
    ImageMvpState,
)
from fourier_sketch.imaging import CannyParameters, EdgeAlgorithm

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("algorithm", tuple(EdgeAlgorithm))
def test_real_image_reaches_shared_endpoint_timeline(
    algorithm: EdgeAlgorithm,
    tmp_path: Path,
) -> None:
    source = tmp_path / f"{algorithm.value}.png"
    image = Image.new("L", (48, 32), 0)
    ImageDraw.Draw(image).ellipse((10, 5, 37, 26), fill=255)
    image.save(source)
    controller = ImageMvpController()
    config = ImageMvpConfig(
        algorithm=algorithm,
        canny_parameters=CannyParameters(low_threshold=40, high_threshold=120),
        sample_count=64,
        harmonic_count=12,
    )

    snapshot = controller.process(controller.begin(config), source)
    snapshot = controller.play()
    snapshot = controller.tick(0.2)

    assert snapshot.state is ImageMvpState.READY
    assert isinstance(snapshot.result, ImageContourTimelineResult)
    assert snapshot.result.preprocessing.grayscale.pixel_count == 48 * 32
    assert snapshot.result.edges.algorithm is algorithm
    assert snapshot.result.selection.extraction.candidate_count >= 1
    assert snapshot.result.sampled_curve.sample_count == 64
    assert snapshot.frame is not None
    assert snapshot.frame.original == snapshot.result.sampled_curve
    assert snapshot.frame.trace[-1] == snapshot.frame.chain.endpoint


def test_dominant_contour_limits_and_selection_remain_observable(tmp_path: Path) -> None:
    source = tmp_path / "two-shapes.png"
    image = Image.new("L", (64, 40), 0)
    drawing = ImageDraw.Draw(image)
    drawing.rectangle((5, 5, 15, 15), fill=255)
    drawing.rectangle((28, 6, 58, 34), fill=255)
    image.save(source)
    controller = ImageMvpController()

    snapshot = controller.process(
        controller.begin(ImageMvpConfig(sample_count=96, harmonic_count=16)),
        source,
    )

    assert isinstance(snapshot.result, ImageContourTimelineResult)
    provenance = snapshot.result.normalized.provenance
    assert provenance.candidate_count == 2
    assert provenance.selected_bounding_box == (28, 6, 58, 34)
    assert provenance.selected_point_count == snapshot.result.selection.candidate.point_count
