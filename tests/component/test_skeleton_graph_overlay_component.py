"""Visible topology overlay and atomic graph artifact contracts."""

import json
from pathlib import Path

import pytest
from matplotlib.figure import Figure
from PIL import Image, ImageDraw

from fourier_sketch.application import (
    LocalSkeletonGraphResult,
    build_local_skeleton_graph,
    export_skeleton_graph_json,
)
from fourier_sketch.presentation import Translator
from fourier_sketch.render import (
    draw_skeleton_graph_overlay,
    render_skeleton_graph_overlay_png,
)

pytestmark = pytest.mark.component


def _result(tmp_path: Path) -> LocalSkeletonGraphResult:
    source = tmp_path / "shape.png"
    image = Image.new("L", (40, 30), 0)
    draw = ImageDraw.Draw(image)
    draw.line((5, 15, 34, 15), fill=255, width=5)
    draw.line((20, 5, 20, 25), fill=255, width=5)
    image.save(source)
    return build_local_skeleton_graph(source)


def test_overlay_exposes_skeleton_components_nodes_and_summary(tmp_path: Path) -> None:
    result = _result(tmp_path)
    figure = Figure(figsize=(9.5, 4.9))
    axes = tuple(figure.subplots(1, 2))

    draw_skeleton_graph_overlay(figure, axes, result, Translator("en"))

    assert [axis.get_title() for axis in axes] == [
        "Lee skeleton",
        "Compressed topology by component",
    ]
    assert len(axes[1].lines) == len(result.graph.edges)
    assert axes[1].get_legend() is not None
    visible = "\n".join(text.get_text() for text in figure.texts)
    assert "corner-suppressed-8-v1" in visible
    assert "Components:" in visible


def test_overlay_png_and_json_are_real_atomic_artifacts(tmp_path: Path) -> None:
    result = _result(tmp_path)
    overlay = tmp_path / "graph.png"
    data = tmp_path / "graph.json"

    render_skeleton_graph_overlay_png(result, overlay, Translator("pseudo"))
    export_skeleton_graph_json(result, data)

    assert overlay.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    with Image.open(overlay) as rendered:
        assert rendered.width >= 1000
        assert rendered.height >= 500
    decoded = json.loads(data.read_bytes())
    assert decoded["schema"] == "fourier-sketch/skeleton-graph-v1"
    assert decoded["components"]


def test_json_no_overwrite_preserves_existing_file(tmp_path: Path) -> None:
    output = tmp_path / "graph.json"
    output.write_bytes(b"user-owned")

    with pytest.raises(FileExistsError):
        export_skeleton_graph_json(_result(tmp_path), output)

    assert output.read_bytes() == b"user-owned"
