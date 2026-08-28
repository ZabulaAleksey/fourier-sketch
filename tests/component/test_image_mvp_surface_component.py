"""Actual Matplotlib controls and visible-state contracts for FS-013."""

from pathlib import Path
from threading import Event

import pytest
from matplotlib.backend_bases import KeyEvent, MouseButton, MouseEvent
from matplotlib.widgets import Button
from PIL import Image, ImageDraw

from fourier_sketch.application import (
    ImageMvpConfig,
    ImageMvpController,
    ImageMvpState,
    preprocess_local_image,
)
from fourier_sketch.imaging import ImagePreprocessingOptions, ImagePreprocessingResult
from fourier_sketch.presentation import Translator
from fourier_sketch.render import (
    ImageMvpSurface,
    create_image_mvp_surface,
    render_image_mvp_png,
)

pytestmark = pytest.mark.component


def _shape(path: Path) -> None:
    image = Image.new("L", (40, 28), 0)
    ImageDraw.Draw(image).rectangle((8, 5, 31, 22), fill=255)
    image.save(path)


def _click(surface: ImageMvpSurface, button: Button) -> None:
    surface.figure.canvas.draw()
    pixel_x, pixel_y = button.ax.transAxes.transform((0.5, 0.5))
    for event_name in ("button_press_event", "button_release_event"):
        event = MouseEvent(
            event_name,
            surface.figure.canvas,
            pixel_x,
            pixel_y,
            button=MouseButton.LEFT,
        )
        surface.figure.canvas.callbacks.process(event_name, event)


def test_actual_controls_process_and_animate_selected_image(tmp_path: Path) -> None:
    source = tmp_path / "shape.png"
    _shape(source)
    surface = create_image_mvp_surface(
        source,
        Translator("en"),
        config=ImageMvpConfig(sample_count=64, harmonic_count=9),
    )
    try:
        surface.controls.threshold_slider.set_val(120)
        surface.controls.sample_slider.set_val(48)
        surface.controls.harmonic_slider.set_val(60)
        surface.controls.preprocessing_checks.set_active(1)
        _click(surface, surface.controls.process_button)
        ready = surface.wait_for_completion()

        assert ready.state is ImageMvpState.READY
        assert ready.config.preprocessing.autocontrast is True
        assert ready.config.preprocessing.threshold == 120
        assert ready.config.sample_count == 48
        assert ready.config.harmonic_count == 48
        assert surface.controls.harmonic_slider.val == 48
        assert len(surface.grayscale_axes.images) == 1
        assert len(surface.binary_axes.images) == 1
        assert len(surface.contour_axes.images) == 1
        assert len(surface.contour_axes.lines) >= 1
        assert surface.epicycle_axes.get_title() == "4. Epicycles and endpoint trace"

        _click(surface, surface.controls.play_button)
        advanced = surface.tick(0.1)
        assert advanced.frame is not None
        assert len(advanced.frame.trace) == 2
        assert advanced.frame.trace[-1] == advanced.frame.chain.endpoint
        _click(surface, surface.controls.restart_button)
        assert surface.snapshot.frame is not None
        assert len(surface.snapshot.frame.trace) == 1
    finally:
        surface.close()


def test_keyboard_start_and_cancel_publish_no_partial_result(tmp_path: Path) -> None:
    source = tmp_path / "shape.png"
    _shape(source)
    started = Event()
    release = Event()

    def blocking_preprocess(
        path: str | Path,
        options: ImagePreprocessingOptions,
    ) -> ImagePreprocessingResult:
        started.set()
        assert release.wait(timeout=5)
        return preprocess_local_image(path, options)

    surface = create_image_mvp_surface(
        source,
        Translator("en"),
        controller=ImageMvpController(preprocess=blocking_preprocess),
    )
    try:
        start = KeyEvent("key_press_event", surface.figure.canvas, key="enter")
        surface.figure.canvas.callbacks.process("key_press_event", start)
        assert started.wait(timeout=2)
        assert surface.snapshot.state is ImageMvpState.PROCESSING

        cancel = KeyEvent("key_press_event", surface.figure.canvas, key="escape")
        surface.figure.canvas.callbacks.process("key_press_event", cancel)
        assert surface.snapshot.state.value == "cancelled"
        assert surface.snapshot.result is None
        release.set()
        assert surface.wait_for_completion().state is ImageMvpState.CANCELLED
    finally:
        release.set()
        surface.close()


def test_cancelled_queued_generation_is_consumed_as_cancelled_state(tmp_path: Path) -> None:
    source = tmp_path / "shape.png"
    _shape(source)
    first_started = Event()
    release_first = Event()
    first_finished = Event()
    calls = 0

    def blocking_first_preprocess(
        path: str | Path,
        options: ImagePreprocessingOptions,
    ) -> ImagePreprocessingResult:
        nonlocal calls
        calls += 1
        if calls == 1:
            first_started.set()
            assert release_first.wait(timeout=5)
            first_finished.set()
        return preprocess_local_image(path, options)

    surface = create_image_mvp_surface(
        source,
        Translator("en"),
        controller=ImageMvpController(preprocess=blocking_first_preprocess),
    )
    try:
        surface.start()
        assert first_started.wait(timeout=2)
        surface.cancel()
        surface.start()
        surface.cancel()

        snapshot = surface.poll()

        assert snapshot.state is ImageMvpState.CANCELLED
        assert snapshot.result is None
        assert calls == 1
        release_first.set()
        assert first_finished.wait(timeout=5)
    finally:
        release_first.set()
        surface.close()


@pytest.mark.parametrize(
    ("payload", "expected_state", "message_fragment"),
    (("blank", ImageMvpState.EMPTY, "No usable"), ("corrupt", ImageMvpState.ERROR, "safely")),
)
def test_empty_and_error_states_are_visible_and_recoverable(
    payload: str,
    expected_state: ImageMvpState,
    message_fragment: str,
    tmp_path: Path,
) -> None:
    source = tmp_path / f"{payload}.png"
    if payload == "blank":
        Image.new("L", (12, 8), 0).save(source)
    else:
        source.write_bytes(b"not an image")
    surface = create_image_mvp_surface(source, Translator("en"))
    try:
        surface.start()
        snapshot = surface.wait_for_completion()

        assert snapshot.state is expected_state
        assert any(
            message_fragment in text.get_text()
            for axes in (
                surface.grayscale_axes,
                surface.binary_axes,
                surface.contour_axes,
                surface.epicycle_axes,
            )
            for text in axes.texts
        )
        assert surface.controls.process_button.active is True
    finally:
        surface.close()


def test_pseudo_locale_expands_initial_surface_and_controls(tmp_path: Path) -> None:
    surface = create_image_mvp_surface(tmp_path / "not-read-yet.png", Translator("pseudo"))
    try:
        surface.figure.canvas.draw()
        visible_text = [
            *(text.get_text() for axes in surface.figure.axes for text in axes.texts),
            surface.controls.process_button.label.get_text(),
            surface.controls.cancel_button.label.get_text(),
        ]
        assert any("[!!" in value for value in visible_text)
        assert "pseudo expansion" in surface.controls.process_button.label.get_text()
    finally:
        surface.close()


def test_no_overwrite_race_preserves_competing_destination(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "blank.png"
    output = tmp_path / "race.png"
    Image.new("L", (8, 8), 0).save(source)
    controller = ImageMvpController()
    snapshot = controller.process(controller.begin(ImageMvpConfig()), source)

    def competing_link(_source: object, _target: object) -> None:
        output.write_bytes(b"competitor-owned")
        raise FileExistsError(output.name)

    monkeypatch.setattr(
        "fourier_sketch.render.matplotlib_image_mvp.os.link",
        competing_link,
    )

    with pytest.raises(FileExistsError):
        render_image_mvp_png(snapshot, output, Translator("en"))

    assert output.read_bytes() == b"competitor-owned"
    assert not tuple(tmp_path.glob(".race.*.tmp"))
