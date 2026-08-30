"""Offscreen component contract for the FS-021 desktop shell."""

import os
import time
from dataclasses import replace
from typing import cast

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QKeyEvent
from PySide6.QtWidgets import QApplication, QCheckBox

from fourier_sketch.application import build_freehand_timeline
from fourier_sketch.domain import Curve, Point2D
from fourier_sketch.ui.desktop import DesktopWindow


def _application() -> QApplication:
    return cast(QApplication, QApplication.instance() or QApplication([]))


def test_desktop_window_uses_pseudo_locale_and_has_a_disabled_future_page() -> None:
    _application()
    window = DesktopWindow(locale="pseudo")

    assert window.windowTitle().startswith("[!! ")
    assert any(not button.isEnabled() for button in window.findChildren(type(window._play)))

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
