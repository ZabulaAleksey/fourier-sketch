"""Actual Qt freehand-to-Solo-to-restore E2E for FS-025."""

import os
import time
from typing import ClassVar, cast

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

from fourier_sketch.ui.desktop import DesktopWindow


class _MemorySettings:
    values: ClassVar[dict[str, object]] = {}

    def __init__(self, *_args: object) -> None:
        pass

    def value(self, key: str, default: object, _type: object) -> object:
        return self.values.get(key, default)

    def setValue(self, key: str, value: object) -> None:
        self.values[key] = value


def _event(event_type: QEvent.Type, point: QPointF, buttons: Qt.MouseButton) -> QMouseEvent:
    button = (
        Qt.MouseButton.LeftButton
        if event_type is not QEvent.Type.MouseMove
        else Qt.MouseButton.NoButton
    )
    return QMouseEvent(
        event_type,
        point,
        point,
        point,
        button,
        buttons,
        Qt.KeyboardModifier.NoModifier,
    )


def test_freehand_keyboard_selection_solo_animation_and_restore(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("fourier_sketch.ui.desktop.QSettings", _MemorySettings)
    app = cast(QApplication, QApplication.instance() or QApplication([]))
    window = DesktopWindow()
    window._source.resize(420, 320)
    window._source.mousePressEvent(
        _event(QEvent.Type.MouseButtonPress, QPointF(70.0, 90.0), Qt.MouseButton.LeftButton)
    )
    window._source.mouseMoveEvent(
        _event(QEvent.Type.MouseMove, QPointF(220.0, 70.0), Qt.MouseButton.LeftButton)
    )
    window._source.mouseReleaseEvent(
        _event(QEvent.Type.MouseButtonRelease, QPointF(340.0, 230.0), Qt.MouseButton.NoButton)
    )

    deadline = time.monotonic() + 3.0
    while window._job is not None and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)
    assert window._timeline is not None
    baseline = window._timeline.snapshot()
    window._inspector_list.setCurrentRow(min(1, window._inspector_list.count() - 1))
    frequency = window._selected_harmonic_frequency
    assert frequency is not None

    window._solo_action.click()
    window._timeline_action("play")
    window._timeline_action("advance", 0.1)
    assert window._current_frame is not None
    assert window._current_frame.selection.frequencies == (frequency,)
    assert len(window._current_frame.chain.vectors) == 1
    assert window._current_frame.trace[-1] == window._current_frame.chain.endpoint
    advanced_baseline = window._timeline.snapshot()
    assert advanced_baseline.selection == baseline.selection
    baseline_before_exit = window._baseline_frame
    assert baseline_before_exit == advanced_baseline

    window._solo_action.click()
    assert window._current_frame is baseline_before_exit
    assert window._current_frame == advanced_baseline
    assert window._timeline.snapshot() == advanced_baseline
    window.close()
