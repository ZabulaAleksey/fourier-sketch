"""Real FS-010 -> FS-014 -> FS-015 integration evidence."""

from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from fourier_sketch.application import build_local_skeleton_graph
from fourier_sketch.imaging import SKELETON_GRAPH_SCHEMA, SkeletonNodeKind

pytestmark = pytest.mark.integration


def test_real_lee_cross_reaches_explicit_graph_topology(tmp_path: Path) -> None:
    source = tmp_path / "cross.png"
    image = Image.new("L", (41, 41), 0)
    draw = ImageDraw.Draw(image)
    draw.line((5, 20, 35, 20), fill=255, width=7)
    draw.line((20, 5, 20, 35), fill=255, width=7)
    image.save(source)

    result = build_local_skeleton_graph(source)

    assert result.graph.source == result.skeleton.skeletonization
    assert result.graph.schema == SKELETON_GRAPH_SCHEMA
    assert result.graph.source.backend.startswith("scikit-image/0.26.")
    assert len(result.graph.components) == 1
    assert result.graph.endpoint_count == 4
    assert result.graph.junction_count == 1
    assert len(result.graph.edges) == 4
    assert any(
        node.kind is SkeletonNodeKind.JUNCTION_REGION for node in result.graph.nodes
    )


def test_real_multi_component_skeleton_is_not_joined(tmp_path: Path) -> None:
    source = tmp_path / "separate.png"
    image = Image.new("L", (48, 32), 0)
    draw = ImageDraw.Draw(image)
    draw.line((4, 8, 19, 8), fill=255, width=5)
    draw.line((29, 24, 44, 24), fill=255, width=5)
    image.save(source)

    graph = build_local_skeleton_graph(source).graph

    assert len(graph.components) == 2
    assert graph.endpoint_count == 4
    assert all(
        graph.nodes[edge.start_node_id].component_id
        == graph.nodes[edge.end_node_id].component_id
        == edge.component_id
        for edge in graph.edges
    )
