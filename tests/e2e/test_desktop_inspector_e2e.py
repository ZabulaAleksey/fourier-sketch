"""Actual Qt pointer-to-inspector E2E for FS-024."""

import os
import time
from typing import ClassVar, cast

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

from fourier_sketch.presentation.harmonic_inspector import (
    build_harmonic_inspector_item,
)
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


def test_freehand_pointer_path_reaches_same_frame_harmonic_inspector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("fourier_sketch.ui.desktop.QSettings", _MemorySettings)
    app = cast(QApplication, QApplication.instance() or QApplication([]))
    window = DesktopWindow()
    window._source.resize(420, 320)

    window._source.mousePressEvent(
        _event(QEvent.Type.MouseButtonPress, QPointF(80.0, 100.0), Qt.MouseButton.LeftButton)
    )
    window._source.mouseMoveEvent(
        _event(QEvent.Type.MouseMove, QPointF(210.0, 60.0), Qt.MouseButton.LeftButton)
    )
    window._source.mouseReleaseEvent(
        _event(QEvent.Type.MouseButtonRelease, QPointF(330.0, 220.0), Qt.MouseButton.NoButton)
    )

    deadline = time.monotonic() + 3.0
    while window._job is not None and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)
    assert window._timeline is not None
    assert window._current_frame is not None
    assert window._inspector_list.count() == len(
        window._current_frame.selection.frequencies
    )

    before = window._timeline.snapshot()
    window._inspector_list.setCurrentRow(min(1, window._inspector_list.count() - 1))
    frequency = window._selected_harmonic_frequency
    assert frequency is not None
    item = build_harmonic_inspector_item(
        window._current_frame.selection,
        window._current_frame.chain,
        frequency,
    )
    assert item is not None
    assert window._inspector_values["frequency"].text() == str(frequency)
    assert window._inspector_values["local_value"].text() == (
        f"{item.local_value.real:+.6g} {item.local_value.imag:+.6g}i"
    )
    assert window._timeline.snapshot() == before
    window.close()
