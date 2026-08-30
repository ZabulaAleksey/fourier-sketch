"""Live FS-022 artifacts reopened through real Pillow/Matplotlib backends."""

import json
from pathlib import Path
from typing import Any, cast

import pytest
from PIL import Image

from fourier_sketch.application import (
    AnimationExportPlan,
    EpicycleFrame,
    ExportCancelled,
    build_freehand_timeline,
)
from fourier_sketch.domain import Curve, Point2D
from fourier_sketch.presentation import Translator
from fourier_sketch.render import export_animation_gif, render_frame_png, render_spectrum_png


def _frame() -> EpicycleFrame:
    curve = Curve(
        (
            Point2D(1.0, 0.0),
            Point2D(0.0, 1.0),
            Point2D(-1.0, 0.0),
            Point2D(0.0, -1.0),
        ),
        closed=True,
    )
    return build_freehand_timeline(curve).snapshot()


def test_real_gif_and_spectrum_png_reopen_with_endpoint_metadata(tmp_path: Path) -> None:
    frame = _frame()
    gif = tmp_path / "animation.gif"
    spectrum = tmp_path / "spectrum.png"
    reconstruction = tmp_path / "reconstruction.png"
    progress: list[int] = []

    export_animation_gif(
        AnimationExportPlan(frame, frame_count=5, frame_duration_ms=40),
        gif,
        Translator("en"),
        progress=progress.append,
    )
    render_spectrum_png(frame.selection, spectrum, Translator("en"))
    render_frame_png(frame, reconstruction, Translator("en"))

    with Image.open(gif) as image:
        assert image.format == "GIF"
        assert cast(Any, image).n_frames == 5
        metadata = json.loads(image.info["comment"].decode("ascii"))
    assert metadata["schema"] == "fourier-sketch.epicycle-animation"
    assert metadata["frame_count"] == 5
    assert len(metadata["endpoints"]) == 5
    assert progress == [20, 40, 60, 80, 100]
    with Image.open(spectrum) as image:
        image.verify()
        assert image.format == "PNG"
    with Image.open(reconstruction) as image:
        image.verify()
        assert image.format == "PNG"


def test_cancelled_gif_leaves_no_partial_artifact(tmp_path: Path) -> None:
    output = tmp_path / "cancelled.gif"
    calls = 0

    def cancelled() -> bool:
        nonlocal calls
        calls += 1
        return calls > 2

    with pytest.raises(ExportCancelled):
        export_animation_gif(
            AnimationExportPlan(_frame(), frame_count=5, frame_duration_ms=40),
            output,
            Translator("en"),
            cancelled=cancelled,
        )

    assert not output.exists()
    assert not tuple(tmp_path.glob(".cancelled.*.tmp"))


def test_gif_codec_failure_leaves_no_partial_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "failed.gif"

    def fail_save(*_args: object, **_kwargs: object) -> None:
        raise OSError("simulated codec failure")

    monkeypatch.setattr(Image.Image, "save", fail_save)
    with pytest.raises(OSError, match="simulated codec failure"):
        export_animation_gif(
            AnimationExportPlan(_frame(), frame_count=2, frame_duration_ms=20),
            output,
            Translator("en"),
        )

    assert not output.exists()
    assert not tuple(tmp_path.glob(".failed.*.tmp"))
