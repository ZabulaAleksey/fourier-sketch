"""Offscreen component contract for the FS-021 desktop shell."""

import json
import os
import time
from dataclasses import replace
from math import cos, pi, sin
from pathlib import Path
from typing import ClassVar, cast

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PIL import Image, ImageDraw
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QImage, QKeyEvent, QMouseEvent, QWheelEvent
from PySide6.QtWidgets import QApplication, QCheckBox, QMessageBox, QPushButton

from fourier_sketch.application import (
    ExportFormat,
    ImageContourTimelineResult,
    TimelineState,
    build_freehand_timeline,
)
from fourier_sketch.domain import Curve, Point2D
from fourier_sketch.ui.desktop import (
    DesktopWindow,
    _gesture_view_transform,
    run_desktop,
)


def _application() -> QApplication:
    return cast(QApplication, QApplication.instance() or QApplication([]))


class _MemorySettings:
    """In-memory QSettings replacement that keeps component tests isolated."""

    values: ClassVar[dict[str, object]] = {}

    def __init__(self, *_args: object) -> None:
        pass

    def value(self, key: str, default: object, _type: object) -> object:
        return self.values.get(key, default)

    def setValue(self, key: str, value: object) -> None:
        self.values[key] = value


@pytest.fixture(autouse=True)
def _desktop_settings_are_isolated(monkeypatch: pytest.MonkeyPatch) -> None:
    _MemorySettings.values = {}
    monkeypatch.setattr("fourier_sketch.ui.desktop.QSettings", _MemorySettings)


def _wait_for_timeline(window: DesktopWindow, *, timeout_seconds: float = 2.0) -> None:
    app = _application()
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        app.processEvents()
        if window._timeline is not None:
            return
        time.sleep(0.01)
    raise AssertionError("Desktop timeline was not produced before timeout")


def _wait_for_job(window: DesktopWindow, *, timeout_seconds: float = 5.0) -> None:
    app = _application()
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        app.processEvents()
        if window._job is None:
            return
        time.sleep(0.01)
    raise AssertionError("Desktop job did not finish before timeout")


def _assert_playback_advances(window: DesktopWindow) -> None:
    assert window._canvas._frame is not None
    trace_length = len(window._canvas._frame.trace)
    window._timeline_action("play")
    window._last_tick -= 0.05
    window._tick()
    assert window._canvas._frame is not None
    assert len(window._canvas._frame.trace) > trace_length


def test_desktop_window_uses_pseudo_locale_and_has_a_disabled_future_page() -> None:
    _application()
    window = DesktopWindow(locale="pseudo")

    assert window.windowTitle().startswith("[!! ")
    assert any(not button.isEnabled() for button in window.findChildren(type(window._play)))

    window.close()


def _mouse_event(
    event_type: QEvent.Type,
    point: QPointF,
    *,
    button: Qt.MouseButton,
    buttons: Qt.MouseButton,
) -> QMouseEvent:
    return QMouseEvent(
        event_type,
        point,
        point,
        point,
        button,
        buttons,
        Qt.KeyboardModifier.NoModifier,
    )


def test_desktop_freehand_flow_generates_animation_frame() -> None:
    _application()
    window = DesktopWindow()

    window._source.mousePressEvent(
        _mouse_event(
            QEvent.Type.MouseButtonPress,
            QPointF(20.0, 20.0),
            button=Qt.MouseButton.LeftButton,
            buttons=Qt.MouseButton.LeftButton,
        )
    )
    window._source.mouseMoveEvent(
        _mouse_event(
            QEvent.Type.MouseMove,
            QPointF(80.0, 45.0),
            button=Qt.MouseButton.NoButton,
            buttons=Qt.MouseButton.LeftButton,
        )
    )
    window._source.mouseReleaseEvent(
        _mouse_event(
            QEvent.Type.MouseButtonRelease,
            QPointF(120.0, 75.0),
            button=Qt.MouseButton.LeftButton,
            buttons=Qt.MouseButton.NoButton,
        )
    )
    _wait_for_timeline(window)

    assert window._timeline is not None
    assert window._canvas._frame is not None
    assert window._canvas._frame.timeline_state is TimelineState.PAUSED

    _assert_playback_advances(window)
    window._timeline_action("pause")
    assert window._canvas._frame.timeline_state is TimelineState.PAUSED
    window.close()


def test_desktop_image_flow_from_file_and_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _application()
    source = tmp_path / "shape.png"
    # The source contract is a dark drawing on a light background.  A white
    # canvas must not be interpreted as a framed black image by preprocessing.
    image = Image.new("L", (24, 18), 255)
    ImageDraw.Draw(image).rectangle((4, 4, 19, 13), outline=0, width=2)
    image.save(source)
    window = DesktopWindow()
    window._speed.setValue(42)

    def fake_open(*_args: object, **_kwargs: object) -> tuple[str, str]:
        return (str(source), "")

    monkeypatch.setattr("fourier_sketch.ui.desktop.QFileDialog.getOpenFileName", fake_open)
    window._choose_image()
    _wait_for_timeline(window, timeout_seconds=6.0)

    assert window._timeline is not None
    assert window._canvas._frame is not None
    assert window._canvas._frame.speed == 0.42
    snapshot = window._image.snapshot()
    assert isinstance(snapshot.result, ImageContourTimelineResult)
    assert snapshot.result.selection.candidate.bounding_box == (4, 4, 19, 13)
    grayscale = snapshot.result.preprocessing.grayscale
    assert grayscale.pixels[0] == 255
    assert grayscale.pixels[5 * grayscale.width + 5] == 0
    assert window._canvas._frame.original.sample_count > 4

    _assert_playback_advances(window)
    window.close()


def test_desktop_restores_non_sensitive_preferences() -> None:
    _application()
    first = DesktopWindow()
    first.resize(720, 540)
    first._speed.setValue(42)
    first._harmonics.setValue(17)
    first._zoom.setValue(175)
    first.close()

    restored = DesktopWindow()

    assert (restored.width(), restored.height()) == (720, 540)
    assert restored._speed.value() == 42
    assert restored._harmonics.value() == 17
    assert restored._zoom.value() == 175
    assert restored._canvas.view_zoom == 1.75
    restored.close()


def test_desktop_canvas_zoom_is_bounded_and_resettable() -> None:
    _application()
    window = DesktopWindow()

    window._canvas.set_view_zoom(1_000_000.0)
    assert window._canvas.view_zoom == 100.0
    window._canvas.set_view_zoom(0.000001)
    assert window._canvas.view_zoom == 0.01

    window._canvas.set_view_zoom(1.8)
    window._canvas.reset_view()
    assert window._canvas.view_zoom == 1.0

    window._zoom.setValue(200)
    assert window._canvas.view_zoom == 2.0
    reset_button = next(
        button
        for button in window.findChildren(QPushButton)
        if button.accessibleName() == "Reset canvas view"
    )
    reset_button.click()
    assert window._zoom.value() == 100
    assert window._canvas.view_zoom == 1.0
    window.close()


def test_desktop_source_field_is_centered_with_epicycle_canvas() -> None:
    app = _application()
    window = DesktopWindow()
    window.resize(1200, 760)
    window.show()
    app.processEvents()

    source = window._source.geometry()
    canvas = window._canvas.geometry()
    source_center_y = source.y() + source.height() / 2.0
    canvas_center_y = canvas.y() + canvas.height() / 2.0

    assert abs(source_center_y - canvas_center_y) <= 1.0
    window.close()


def test_desktop_freehand_screen_y_is_converted_to_cartesian_y() -> None:
    _application()
    window = DesktopWindow()
    source = window._source
    center = QPointF(source.width() / 2.0, source.height() / 2.0)

    # The center of the drawing field is the Cartesian origin and the start
    # of the head-to-tail chain. Screen Y still grows downward.
    assert source._point(center) == Point2D(0.0, 0.0)
    assert source._point(QPointF(center.x() + 31.0, center.y() - 24.0)) == Point2D(31.0, 24.0)
    assert source._screen_point(Point2D(31.0, 24.0)) == QPointF(
        center.x() + 31.0, center.y() - 24.0
    )
    window.close()


def test_new_freehand_curve_resets_to_source_relative_100_percent_and_syncs_original() -> None:
    _application()
    window = DesktopWindow()
    source = window._source
    canvas = window._canvas
    source.resize(600, 400)
    canvas.resize(300, 200)
    original = window._visibility_toggles["original"]

    assert not original.isEnabled()
    assert not original.isChecked()

    canvas.set_view_zoom(2.5)
    canvas._apply_touch_points({1: (50.0, 50.0)}, {1: (70.0, 40.0)})
    source.mousePressEvent(
        _mouse_event(
            QEvent.Type.MouseButtonPress,
            QPointF(150.0, 100.0),
            button=Qt.MouseButton.LeftButton,
            buttons=Qt.MouseButton.LeftButton,
        )
    )
    source.mouseMoveEvent(
        _mouse_event(
            QEvent.Type.MouseMove,
            QPointF(300.0, 200.0),
            button=Qt.MouseButton.NoButton,
            buttons=Qt.MouseButton.LeftButton,
        )
    )
    source.mouseReleaseEvent(
        _mouse_event(
            QEvent.Type.MouseButtonRelease,
            QPointF(450.0, 300.0),
            button=Qt.MouseButton.LeftButton,
            buttons=Qt.MouseButton.NoButton,
        )
    )
    _wait_for_timeline(window)

    assert canvas.view_zoom == 1.0
    assert canvas.view_pan == (0.0, 0.0)
    scale, center_x, center_y = canvas._scene_transform()
    assert scale == pytest.approx(
        min(canvas.width() / source.width(), canvas.height() / source.height())
    )
    assert (center_x, center_y) == (0.0, 0.0)
    assert original.isEnabled()
    assert original.isChecked()
    assert canvas._frame is not None and canvas._frame.visibility.original

    original.click()
    assert not original.isChecked()
    assert canvas._frame is not None and not canvas._frame.visibility.original

    window._apply_timeline(
        build_freehand_timeline(Curve((Point2D(-1.0, 0.0), Point2D(1.0, 0.0)), closed=False))
    )
    assert original.isChecked()
    assert canvas._frame is not None and canvas._frame.visibility.original
    window.close()


def test_desktop_canvas_zoom_preserves_pan_and_left_drag_reset_view() -> None:
    _application()
    window = DesktopWindow()
    canvas = window._canvas

    canvas.mousePressEvent(
        _mouse_event(
            QEvent.Type.MouseButtonPress,
            QPointF(100.0, 100.0),
            button=Qt.MouseButton.LeftButton,
            buttons=Qt.MouseButton.LeftButton,
        )
    )
    canvas.mouseMoveEvent(
        _mouse_event(
            QEvent.Type.MouseMove,
            QPointF(135.0, 82.0),
            button=Qt.MouseButton.NoButton,
            buttons=Qt.MouseButton.LeftButton,
        )
    )
    canvas.mouseReleaseEvent(
        _mouse_event(
            QEvent.Type.MouseButtonRelease,
            QPointF(135.0, 82.0),
            button=Qt.MouseButton.LeftButton,
            buttons=Qt.MouseButton.NoButton,
        )
    )
    panned = canvas.view_pan
    assert panned == (35.0, -18.0)
    centered_scene_offset = tuple(-value / canvas.view_zoom for value in panned)

    canvas.wheelEvent(
        QWheelEvent(
            QPointF(120.0, 100.0),
            QPointF(120.0, 100.0),
            QPoint(0, 0),
            QPoint(0, 120),
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
            Qt.ScrollPhase.NoScrollPhase,
            False,
        )
    )
    assert canvas.view_zoom > 1.0
    assert window._zoom.value() == round(canvas.view_zoom * 100)
    assert tuple(-value / canvas.view_zoom for value in canvas.view_pan) == pytest.approx(
        centered_scene_offset
    )

    window._zoom.setValue(250)
    assert canvas.view_zoom == 2.5
    assert tuple(-value / canvas.view_zoom for value in canvas.view_pan) == pytest.approx(
        centered_scene_offset
    )

    canvas.reset_view()
    assert canvas.view_zoom == 1.0
    assert canvas.view_pan == (0.0, 0.0)
    window.close()


def test_touch_gesture_math_pans_with_one_finger_and_keeps_pinch_center_fixed() -> None:
    panned_zoom, panned = _gesture_view_transform(
        zoom=1.0,
        pan=(4.0, -3.0),
        previous_points=((20.0, 30.0),),
        current_points=((32.0, 25.0),),
    )
    assert panned_zoom == 1.0
    assert panned == (16.0, -8.0)

    old_zoom = 2.0
    old_pan = (10.0, -5.0)
    next_zoom, next_pan = _gesture_view_transform(
        zoom=old_zoom,
        pan=old_pan,
        previous_points=((110.0, 100.0), (130.0, 100.0)),
        current_points=((100.0, 100.0), (140.0, 100.0)),
    )
    assert next_zoom == 4.0
    assert next_pan == (20.0, -10.0)

    fractional_zoom, fractional_pan = _gesture_view_transform(
        zoom=1.0,
        pan=(0.0, 0.0),
        previous_points=((100.0, 100.0), (120.0, 100.0)),
        current_points=((98.77, 100.0), (121.23, 100.0)),
    )
    assert fractional_zoom == 1.12
    assert fractional_pan == (0.0, 0.0)


def test_desktop_touch_pan_and_pinch_are_presentation_only_and_resettable() -> None:
    _application()
    window = DesktopWindow()
    timeline = build_freehand_timeline(
        Curve(
            (
                Point2D(1.0, 0.0),
                Point2D(0.7, 0.7),
                Point2D(0.0, 1.0),
                Point2D(-0.7, 0.7),
                Point2D(-1.0, 0.0),
                Point2D(-0.7, -0.7),
                Point2D(0.0, -1.0),
                Point2D(0.7, -0.7),
            ),
            closed=True,
        )
    )
    window._apply_timeline(timeline)
    canvas = window._canvas
    canvas.resize(400, 300)
    frame_before = canvas._frame
    timeline_before = timeline.snapshot()
    timer_before = window._timer.isActive()

    canvas._apply_touch_points({1: (80.0, 90.0)}, {1: (105.0, 75.0)})
    assert canvas.view_pan == (25.0, -15.0)

    canvas._apply_touch_points(
        {1: (90.0, 100.0), 2: (110.0, 100.0)},
        {1: (80.0, 100.0), 2: (120.0, 100.0)},
    )
    assert canvas.view_zoom == 2.0
    assert canvas.view_pan == (50.0, -30.0)
    assert window._zoom.value() == 200
    assert canvas._frame is frame_before
    assert timeline.snapshot() == timeline_before
    assert window._timer.isActive() is timer_before

    canvas._apply_touch_points(
        {1: (99.5, 100.0), 2: (100.5, 100.0)},
        {1: (-900.0, 100.0), 2: (1100.0, 100.0)},
    )
    assert canvas.view_zoom == 100.0
    assert window._zoom.value() == 10_000

    canvas._apply_touch_points(
        {1: (-900.0, 100.0), 2: (1100.0, 100.0)},
        {1: (99.95, 100.0), 2: (100.05, 100.0)},
    )
    assert canvas.view_zoom == 0.01
    assert window._zoom.value() == 1

    canvas._touch_points = {1: (100.0, 100.0)}
    canvas.reset_view()
    assert canvas.view_zoom == 1.0
    assert canvas.view_pan == (0.0, 0.0)
    assert canvas._touch_points == {}
    assert window._zoom.value() == 100
    window.close()


def test_desktop_cli_does_not_override_restored_window_size(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _DesktopWindowStub:
        def __init__(self, *, locale: str | None = None) -> None:
            self.locale = locale
            self.was_shown = False
            self.resize_calls = 0
            created.append(self)

        def resize(self, _width: int, _height: int) -> None:
            self.resize_calls += 1

        def show(self) -> None:
            self.was_shown = True

    created: list[_DesktopWindowStub] = []

    class _ApplicationStub:
        @staticmethod
        def instance() -> None:
            return None

        def __init__(self, _args: list[str]) -> None:
            pass

        def exec(self) -> int:
            return 0

    monkeypatch.setattr("fourier_sketch.ui.desktop.DesktopWindow", _DesktopWindowStub)
    monkeypatch.setattr("fourier_sketch.ui.desktop.QApplication", _ApplicationStub)

    assert run_desktop(locale="pseudo") == 0
    assert len(created) == 1
    assert created[0].locale == "pseudo"
    assert created[0].was_shown
    assert created[0].resize_calls == 0


def test_desktop_resets_legacy_speed_preference_to_safe_minimum() -> None:
    _application()
    _MemorySettings.values = {"controls/speed": 40}

    window = DesktopWindow()

    assert window._speed.value() == window._speed.minimum()
    window.close()


def test_desktop_window_renders_existing_timeline_and_keyboard_controls_are_enabled() -> None:
    _application()
    window = DesktopWindow()
    assert not window._timer.isActive()
    timeline = build_freehand_timeline(
        Curve((Point2D(0.0, 0.0), Point2D(1.0, 0.0), Point2D(0.5, 1.0)), closed=True)
    )

    window._apply_timeline(timeline)

    assert window._canvas._frame is not None
    assert len(window._canvas._vector_colors) == len(window._canvas._frame.chain.vectors)
    assert len({color.name() for color in window._canvas._vector_colors}) == len(
        window._canvas._vector_colors
    )
    assert window._play.isEnabled()
    assert not window._cancel.isEnabled()
    assert window._harmonics.minimum() == 1
    assert window._speed.minimum() == 1
    assert window._speed.maximum() == 100
    assert window._speed.singleStep() == 1
    window._speed.setValue(42)
    assert window._canvas._frame.speed == 0.42
    window._speed.setValue(window._speed.minimum())
    assert window._speed.value() == window._speed.minimum()
    assert window._speed.value() / 100.0 == 0.01
    assert window._canvas._frame.speed == 0.01
    assert not window._timer.isActive()
    assert not any(
        "trace" in checkbox.text().lower() for checkbox in window.findChildren(QCheckBox)
    )

    window._set_visibility("trace", False)
    assert window._canvas._frame is not None
    assert not window._canvas._frame.visibility.trace

    window._speed.setValue(100)
    assert window._canvas._frame.speed == 1.00

    window.keyPressEvent(
        QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Space, Qt.KeyboardModifier.NoModifier)
    )
    assert window._canvas._frame.timeline_state.value == "running"
    assert window._timer.isActive()
    window.keyPressEvent(
        QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Space, Qt.KeyboardModifier.NoModifier)
    )
    assert window._canvas._frame.timeline_state.value == "paused"
    assert not window._timer.isActive()

    window.close()


def test_desktop_rainbow_pairs_stay_stable_when_harmonic_count_grows() -> None:
    _application()
    window = DesktopWindow()
    timeline = build_freehand_timeline(
        Curve(
            (
                Point2D(1.0, 0.0),
                Point2D(0.7, 0.7),
                Point2D(0.0, 1.0),
                Point2D(-0.7, 0.7),
                Point2D(-1.0, 0.0),
                Point2D(-0.7, -0.7),
                Point2D(0.0, -1.0),
                Point2D(0.7, -0.7),
            ),
            closed=True,
        )
    )
    window._apply_timeline(timeline)

    window._harmonics.setValue(3)
    first_colors = tuple(color.name() for color in window._canvas._vector_colors)
    assert len(first_colors) == 3
    assert len(set(first_colors)) == 3
    assert first_colors == tuple(color.name() for color in window._canvas._circle_colors)

    window._harmonics.setValue(8)
    expanded_colors = tuple(color.name() for color in window._canvas._vector_colors)
    assert len(expanded_colors) == 8
    assert len(set(expanded_colors)) == 8
    assert expanded_colors[:3] == first_colors
    assert expanded_colors == tuple(color.name() for color in window._canvas._circle_colors)

    window.close()


def test_desktop_export_page_writes_current_curve_and_reports_mp4_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _application()
    window = DesktopWindow()
    timeline = build_freehand_timeline(
        Curve(
            (
                Point2D(1.0, 0.0),
                Point2D(0.0, 1.0),
                Point2D(-1.0, 0.0),
                Point2D(0.0, -1.0),
            ),
            closed=True,
        )
    )
    window._apply_timeline(timeline)
    output = tmp_path / "curve.json"
    monkeypatch.setattr(
        "fourier_sketch.ui.desktop.QFileDialog.getSaveFileName",
        lambda *_args, **_kwargs: (str(output), "JSON (*.json)"),
    )

    window._export_format.setCurrentIndex(
        window._export_format.findData(ExportFormat.CURVE_JSON.value)
    )
    assert window._export_nav.isEnabled()
    assert window._export_action.isEnabled()
    window._choose_export()
    _wait_for_job(window)

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema"] == "fourier-sketch.curve"
    assert payload["points"] == [
        {"x": point.x, "y": point.y} for point in timeline.snapshot().original.points
    ]
    assert output.name in window._status.text()

    window._export_format.setCurrentIndex(window._export_format.findData(ExportFormat.MP4.value))
    assert not window._export_action.isEnabled()
    assert "MP4" in window._status.text()
    window.close()


def test_desktop_export_requires_explicit_overwrite(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _application()
    window = DesktopWindow()
    timeline = build_freehand_timeline(Curve((Point2D(0.0, 0.0), Point2D(1.0, 1.0)), closed=False))
    window._apply_timeline(timeline)
    output = tmp_path / "curve.json"
    output.write_text("keep", encoding="utf-8")
    monkeypatch.setattr(
        "fourier_sketch.ui.desktop.QFileDialog.getSaveFileName",
        lambda *_args, **_kwargs: (str(output), "JSON (*.json)"),
    )
    monkeypatch.setattr(
        "fourier_sketch.ui.desktop.QMessageBox.question",
        lambda *_args, **_kwargs: QMessageBox.StandardButton.No,
    )
    window._export_format.setCurrentIndex(
        window._export_format.findData(ExportFormat.CURVE_JSON.value)
    )

    window._choose_export()

    assert output.read_text(encoding="utf-8") == "keep"
    assert window._job is None

    monkeypatch.setattr(
        "fourier_sketch.ui.desktop.QMessageBox.question",
        lambda *_args, **_kwargs: QMessageBox.StandardButton.Yes,
    )
    window._choose_export()
    _wait_for_job(window)

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema"] == "fourier-sketch.curve"
    window.close()


def test_desktop_export_page_runs_real_gif_worker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _application()
    window = DesktopWindow()
    timeline = build_freehand_timeline(
        Curve(
            (
                Point2D(1.0, 0.0),
                Point2D(0.0, 1.0),
                Point2D(-1.0, 0.0),
                Point2D(0.0, -1.0),
            ),
            closed=True,
        )
    )
    window._apply_timeline(timeline)
    output = tmp_path / "desktop.gif"
    monkeypatch.setattr(
        "fourier_sketch.ui.desktop.QFileDialog.getSaveFileName",
        lambda *_args, **_kwargs: (str(output), "GIF (*.gif)"),
    )
    window._export_format.setCurrentIndex(window._export_format.findData(ExportFormat.GIF.value))
    window._export_frames.setValue(2)
    window._export_duration.setValue(20)
    statuses: list[str] = []
    original_set_status = window._set_status

    def record_status(text: str) -> None:
        statuses.append(text)
        original_set_status(text)

    monkeypatch.setattr(window, "_set_status", record_status)

    window._choose_export()
    _wait_for_job(window, timeout_seconds=10.0)

    with Image.open(output) as image:
        assert image.format == "GIF"
        assert image.info["comment"]
    assert any("%" in status for status in statuses)
    assert output.name in window._status.text()
    window.close()


def test_desktop_cancelled_real_gif_worker_leaves_no_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _application()
    window = DesktopWindow()
    timeline = build_freehand_timeline(
        Curve(
            tuple(
                Point2D(
                    cos(2.0 * pi * index / 96),
                    sin(2.0 * pi * index / 96),
                )
                for index in range(96)
            ),
            closed=True,
        )
    )
    window._apply_timeline(timeline)
    output = tmp_path / "cancelled-desktop.gif"
    monkeypatch.setattr(
        "fourier_sketch.ui.desktop.QFileDialog.getSaveFileName",
        lambda *_args, **_kwargs: (str(output), "GIF (*.gif)"),
    )
    window._export_format.setCurrentIndex(window._export_format.findData(ExportFormat.GIF.value))
    window._export_frames.setValue(120)
    window._export_duration.setValue(20)

    window._choose_export()
    assert window._job is not None
    window._cancel_current_job()

    assert not output.exists()
    assert not tuple(tmp_path.glob(".cancelled-desktop.*.tmp"))
    assert window._status.text() == window._translator.text("desktop.status.cancelled")
    window.close()


def test_desktop_canvas_pixels_do_not_depend_on_persistent_trace_history() -> None:
    _application()
    window = DesktopWindow()
    timeline = build_freehand_timeline(
        Curve((Point2D(0.0, 0.0), Point2D(1.0, 0.0), Point2D(0.5, 1.0)), closed=True)
    )
    frame = timeline.snapshot()
    alternate_trace = replace(
        frame,
        trace=(Point2D(-1_000.0, -1_000.0), frame.chain.endpoint),
    )

    first = QImage(640, 480, QImage.Format.Format_ARGB32)
    second = QImage(640, 480, QImage.Format.Format_ARGB32)
    window._canvas.resize(640, 480)
    window._canvas.set_frame(frame)
    window._canvas.render(first)
    window._canvas.set_frame(alternate_trace)
    window._canvas.render(second)

    assert first == second

    window.close()


def test_desktop_window_resize_keeps_canvas_ready_for_render() -> None:
    _application()
    window = DesktopWindow()
    timeline = build_freehand_timeline(
        Curve(
            (Point2D(0.0, 0.0), Point2D(1.0, 0.0), Point2D(0.5, 1.0)),
            closed=True,
        )
    )

    frame = timeline.snapshot()
    window._canvas.set_frame(frame)
    first_size = (640, 480)
    second_size = (820, 620)
    first = QImage(*first_size, QImage.Format.Format_ARGB32)
    second = QImage(*second_size, QImage.Format.Format_ARGB32)
    window._canvas.resize(*first_size)
    window._canvas.render(first)
    window._canvas.resize(*second_size)
    window._canvas.render(second)

    # No exception and cache invalidation on resize should preserve interactive state.
    assert window._canvas._frame is frame
    assert window._canvas._frame and window._canvas._frame.original.sample_count == 3

    window.close()


def test_desktop_window_cancel_then_close_stops_timer_and_job() -> None:
    _application()
    window = DesktopWindow()

    def slow_operation() -> object:
        time.sleep(0.2)
        return build_freehand_timeline(
            Curve(
                (Point2D(0.0, 0.0), Point2D(1.0, 0.0), Point2D(0.5, 1.0)),
                closed=True,
            )
        )

    window._start_job(slow_operation, window._apply_timeline)
    assert window._job is not None and window._job.isRunning()
    assert window._cancel.isEnabled()
    window._cancel_current_job()
    assert window._timer.isActive() is False
    assert not window._cancel.isEnabled()
    assert window._status.text() == window._translator.text("desktop.status.cancelled")
    window.close()


def test_desktop_cancel_keeps_a_stubborn_job_owned_until_it_stops() -> None:
    _application()
    window = DesktopWindow()

    class _StubbornJob:
        def __init__(self) -> None:
            self.interruption_requested = False
            self.terminated = False
            self.deleted = False

        def isRunning(self) -> bool:
            return True

        def requestInterruption(self) -> None:
            self.interruption_requested = True

        def wait(self, _milliseconds: int) -> None:
            pass

        def terminate(self) -> None:
            self.terminated = True

        def deleteLater(self) -> None:
            self.deleted = True

    job = _StubbornJob()
    window._job = cast(object, job)  # type: ignore[assignment]

    window._cancel_current_job()

    assert job.interruption_requested
    assert job.terminated
    assert not job.deleted
    assert cast(object, window._job) is job
    assert window._status.text() == window._translator.text("desktop.status.cancelled")
    window.close()


def test_desktop_cancelled_job_does_not_apply_stale_timeline() -> None:
    _application()
    window = DesktopWindow()

    def delayed_operation() -> object:
        time.sleep(0.2)
        return build_freehand_timeline(
            Curve(
                (Point2D(0.0, 0.0), Point2D(1.0, 0.0), Point2D(0.5, 1.0)),
                closed=True,
            )
        )

    window._start_job(delayed_operation, window._apply_timeline)
    window._cancel_current_job()

    time.sleep(0.25)
    assert window._timeline is None

    window.close()
