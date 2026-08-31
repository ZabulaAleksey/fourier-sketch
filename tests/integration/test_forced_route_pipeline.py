"""Real FS-010 -> FS-017 route and Fourier integration evidence."""

from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from fourier_sketch.application import build_local_forced_route, compare_local_forced_routes
from fourier_sketch.routing import ForcedRouteAlgorithm, ForcedRouteStatus

pytestmark = pytest.mark.integration


def _branched_components(path: Path) -> None:
    image = Image.new("L", (72, 40), 0)
    draw = ImageDraw.Draw(image)
    draw.line((6, 12, 30, 12), fill=255, width=5)
    draw.line((18, 4, 18, 21), fill=255, width=5)
    draw.line((45, 30, 65, 30), fill=255, width=5)
    image.save(path)


def test_real_branched_disconnected_image_reaches_forced_route_timeline(tmp_path: Path) -> None:
    source = tmp_path / "route.png"
    _branched_components(source)

    result = build_local_forced_route(source, sample_count=64, harmonic_count=12)

    assert result.routing.status is ForcedRouteStatus.READY
    assert result.routing.curve is not None and result.routing.curve.closed
    assert result.routing.metrics is not None
    assert result.routing.metrics.duplicated_steps > 0
    assert result.routing.metrics.bridge_steps == 2
    assert result.sampled_curve is not None and result.sampled_curve.sample_count == 64
    assert result.timeline is not None
    result.timeline.play()
    frame = result.timeline.advance(1.0 / 60.0)
    assert frame.trace[-1] == frame.chain.endpoint


def test_real_image_compares_two_routes_over_one_immutable_graph(tmp_path: Path) -> None:
    source = tmp_path / "comparison.png"
    _branched_components(source)

    comparison = compare_local_forced_routes(source, sample_count=64, harmonic_count=12)

    assert comparison.baseline.skeleton_graph == comparison.improved.skeleton_graph
    assert comparison.baseline.skeleton_graph is comparison.skeleton_graph
    assert (
        comparison.baseline.routing.algorithm
        is ForcedRouteAlgorithm.BASELINE_TREE_T_JOIN_V1
    )
    assert (
        comparison.improved.routing.algorithm
        is ForcedRouteAlgorithm.GREEDY_SHORTEST_ODD_PAIRING_V1
    )
    assert comparison.baseline.timeline is not None
    assert comparison.improved.timeline is not None
    assert comparison.added_length_delta is not None
