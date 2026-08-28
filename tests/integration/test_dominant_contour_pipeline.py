"""Real FS-010/011/012 image-to-timeline integration paths."""

from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from fourier_sketch.application import (
    ImageContourTimelineResult,
    ImageNoContourResult,
    build_dominant_contour_timeline,
    preprocess_local_image,
)
from fourier_sketch.imaging import CannyParameters, EdgeAlgorithm

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("algorithm", tuple(EdgeAlgorithm))
def test_real_edges_flow_to_resampled_curve_and_actual_endpoint_trace(
    algorithm: EdgeAlgorithm,
    tmp_path: Path,
) -> None:
    source = tmp_path / f"shape-{algorithm.value}.png"
    image = Image.new("L", (40, 28), 0)
    ImageDraw.Draw(image).ellipse((8, 4, 31, 23), fill=255)
    image.save(source)

    result = build_dominant_contour_timeline(
        preprocess_local_image(source),
        algorithm,
        sample_count=64,
        harmonic_count=12,
        canny_parameters=CannyParameters(low_threshold=40, high_threshold=120),
    )

    assert isinstance(result, ImageContourTimelineResult)
    assert result.edges.algorithm is algorithm
    assert result.selection.extraction.candidate_count >= 1
    assert result.normalized.curve.closed
    assert result.sampled_curve.sample_count == 64
    assert result.normalized.provenance.extraction_backend.startswith("opencv/")
    result.timeline.play()
    first = result.timeline.advance(1.0 / 60.0)
    second = result.timeline.advance(1.0 / 60.0)
    assert first.trace[-1] == first.chain.endpoint
    assert second.trace[-1] == second.chain.endpoint
    assert len(second.trace) == 3


def test_blank_image_returns_no_contour_without_curve_or_timeline(tmp_path: Path) -> None:
    source = tmp_path / "blank.png"
    Image.new("L", (12, 8), 0).save(source)

    result = build_dominant_contour_timeline(
        preprocess_local_image(source),
        EdgeAlgorithm.THRESHOLD_BOUNDARY,
    )

    assert isinstance(result, ImageNoContourResult)
    assert result.edges.is_empty
    assert result.no_contour.extraction.candidates == ()
