"""Visible preview and atomic-export contracts for FS-014."""

from pathlib import Path

import pytest
from matplotlib.figure import Figure
from PIL import Image, ImageDraw

from fourier_sketch.application import LocalSkeletonResult, SkeletonConfig, build_local_skeleton
from fourier_sketch.presentation import Translator
from fourier_sketch.render import draw_skeleton_preview, render_skeleton_preview_png

pytestmark = pytest.mark.component


def _result(tmp_path: Path) -> LocalSkeletonResult:
    source = tmp_path / "shape.png"
    image = Image.new("L", (40, 28), 0)
    ImageDraw.Draw(image).rectangle((8, 5, 31, 22), fill=255)
    image.save(source)
    return build_local_skeleton(source, SkeletonConfig())


def test_actual_two_panel_preview_exposes_source_result_and_provenance(tmp_path: Path) -> None:
    result = _result(tmp_path)
    figure = Figure(figsize=(9, 4.8))
    axes = tuple(figure.subplots(1, 2))

    draw_skeleton_preview(figure, axes, result, Translator("en"))

    assert [axis.get_title() for axis in axes] == ["Binary source", "Lee skeleton"]
    assert all(len(axis.images) == 1 for axis in axes)
    visible_text = "\n".join(text.get_text() for text in figure.texts)
    assert "lee" in visible_text
    assert "scikit-image/" in visible_text
    assert "Foreground pixels" in visible_text


def test_preview_png_is_real_and_pseudo_localized(tmp_path: Path) -> None:
    output = tmp_path / "preview.png"

    render_skeleton_preview_png(_result(tmp_path), output, Translator("pseudo"))

    assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    with Image.open(output) as rendered:
        assert rendered.width >= 1000
        assert rendered.height >= 500


def test_no_overwrite_race_preserves_competing_destination(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "race.png"
    result = _result(tmp_path)

    def competing_link(_source: object, _target: object) -> None:
        output.write_bytes(b"competitor-owned")
        raise FileExistsError(output.name)

    monkeypatch.setattr(
        "fourier_sketch.render.matplotlib_skeleton.os.link",
        competing_link,
    )

    with pytest.raises(FileExistsError):
        render_skeleton_preview_png(result, output, Translator("en"))

    assert output.read_bytes() == b"competitor-owned"
    assert not tuple(tmp_path.glob(".race.*.tmp"))
