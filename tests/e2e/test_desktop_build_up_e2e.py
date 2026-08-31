"""Actual Qt freehand-to-Build-Up-to-restore E2E for FS-026."""

import os
import time
from typing import ClassVar, cast

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

from fourier_sketch.application import BuildUpState
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


def _assert_state(window: DesktopWindow, expected: BuildUpState) -> None:
    assert window._build_up.state is expected


def test_freehand_build_up_pause_restart_complete_and_exact_restore(
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
    baseline = window._baseline_frame
    assert baseline is not None
    target = min(3, window._build_up_target.maximum())
    assert target >= 2
    window._build_up_target.setValue(target)
    window._build_up_dwell.setValue(100)

    window._build_up_action.click()
    _assert_state(window, BuildUpState.RUNNING)
    assert window._current_frame is not None
    assert window._current_frame.selection.coefficient_count == 1
    assert window._current_frame.trace == (window._current_frame.chain.endpoint,)
    window._timeline_action("advance", 0.1)
    assert window._current_frame.selection.coefficient_count == 2
    window._timeline_action("pause")
    window._timeline_action("advance", 1.0)
    assert window._current_frame.selection.coefficient_count == 2
    window._timeline_action("restart")
    assert window._current_frame.selection.coefficient_count == 1
    window._timeline_action("play")
    for _ in range(target - 1):
        window._timeline_action("advance", 0.1)
    _assert_state(window, BuildUpState.COMPLETED)
    assert window._current_frame.selection.coefficient_count == target
    assert window._timeline.snapshot() == baseline

    window._build_up_action.click()
    assert window._current_frame is baseline
    assert window._timeline.snapshot() == baseline
    window.close()
