"""Offscreen component contract for the FS-021 desktop shell."""

import os
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
    assert window._speed.minimum() == 2
    assert window._speed.maximum() == 40
    assert window._speed.singleStep() == 1
    assert window._speed.value() / 20.0 == 0.10
    assert window._canvas._frame.speed == 0.10
    assert not window._timer.isActive()
    assert not any(
        "trace" in checkbox.text().lower() for checkbox in window.findChildren(QCheckBox)
    )

    window._set_visibility("trace", False)
    assert window._canvas._frame is not None
    assert not window._canvas._frame.visibility.trace

    window._speed.setValue(40)
    assert window._canvas._frame.speed == 2.00

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
