"""Offscreen component contract for the FS-021 desktop shell."""

import os
from typing import cast

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication

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
    timeline = build_freehand_timeline(
        Curve((Point2D(0.0, 0.0), Point2D(1.0, 0.0), Point2D(0.5, 1.0)), closed=True)
    )

    window._apply_timeline(timeline)

    assert window._canvas._frame is not None
    assert window._play.isEnabled()
    assert window._harmonics.minimum() == 1

    window._set_visibility("trace", False)
    assert window._canvas._frame is not None
    assert not window._canvas._frame.visibility.trace

    window.keyPressEvent(
        QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Space, Qt.KeyboardModifier.NoModifier)
    )
    assert window._canvas._frame.timeline_state.value == "running"

    window.close()
