"""Offscreen component contract for the FS-021 desktop shell."""

import os
import time
from dataclasses import replace
from pathlib import Path
from typing import ClassVar, cast

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PIL import Image, ImageDraw
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QImage, QKeyEvent, QMouseEvent
from PySide6.QtWidgets import QApplication, QCheckBox

from fourier_sketch.application import TimelineState, build_freehand_timeline
from fourier_sketch.domain import Curve, Point2D
from fourier_sketch.ui.desktop import DesktopWindow, run_desktop


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
    image = Image.new("L", (24, 18), 0)
    ImageDraw.Draw(image).rectangle((4, 4, 19, 13), outline=255, width=2)
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

    _assert_playback_advances(window)
    window.close()


def test_desktop_restores_non_sensitive_preferences() -> None:
    _application()
    first = DesktopWindow()
    first.resize(720, 540)
    first._speed.setValue(42)
    first._harmonics.setValue(17)
    first.close()

    restored = DesktopWindow()

    assert (restored.width(), restored.height()) == (720, 540)
    assert restored._speed.value() == 42
    assert restored._harmonics.value() == 17
    restored.close()


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
    assert window._play.isEnabled()
    assert window._harmonics.minimum() == 1
    assert window._speed.minimum() == 10
    assert window._speed.maximum() == 100
    assert window._speed.singleStep() == 1
    window._speed.setValue(42)
    assert window._canvas._frame.speed == 0.42
    window._speed.setValue(window._speed.minimum())
    assert window._speed.value() == window._speed.minimum()
    assert window._speed.value() / 100.0 == 0.10
    assert window._canvas._frame.speed == 0.10
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
    window._cancel_current_job()
    assert window._timer.isActive() is False
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
