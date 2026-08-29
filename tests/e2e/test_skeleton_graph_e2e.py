"""Live subprocess evidence for the FS-015 graph diagnostic."""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

pytestmark = pytest.mark.e2e


def _run_cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "fourier_sketch.cli.skeleton_graph", *arguments],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )


def _cross(path: Path) -> None:
    image = Image.new("L", (48, 32), 0)
    draw = ImageDraw.Draw(image)
    draw.line((7, 16, 40, 16), fill=255, width=7)
    draw.line((24, 5, 24, 27), fill=255, width=7)
    image.save(path)


def test_local_image_reaches_canonical_graph_json(tmp_path: Path) -> None:
    source = tmp_path / "cross.png"
    output = tmp_path / "graph.json"
    _cross(source)

    completed = _run_cli(str(source), "--output", str(output))

    assert completed.returncode == 0, completed.stderr
    decoded = json.loads(output.read_bytes())
    assert decoded["schema"] == "fourier-sketch/skeleton-graph-v1"
    assert decoded["skeleton_algorithm"] == "lee"
    assert len(decoded["components"]) == 1
    assert "4 endpoints" in completed.stdout
    assert "1 junctions" in completed.stdout


def test_local_image_reaches_topology_overlay(tmp_path: Path) -> None:
    source = tmp_path / "cross.png"
    output = tmp_path / "graph.png"
    _cross(source)

    completed = _run_cli(
        str(source),
        "--mode",
        "overlay",
        "--output",
        str(output),
        "--locale",
        "pseudo",
    )

    assert completed.returncode == 0, completed.stderr
    with Image.open(output) as rendered:
        assert rendered.width >= 1000
        assert rendered.height >= 500
    assert "[!!" in completed.stdout


def test_existing_output_and_corrupt_input_fail_without_data_loss(tmp_path: Path) -> None:
    source = tmp_path / "private-corrupt.png"
    output = tmp_path / "graph.json"
    source.write_bytes(b"not an image")
    output.write_bytes(b"user-owned")

    completed = _run_cli(str(source), "--output", str(output))

    assert completed.returncode == 2
    assert output.read_bytes() == b"user-owned"
    assert str(source) not in completed.stderr
    assert "safely decoded" in completed.stderr
