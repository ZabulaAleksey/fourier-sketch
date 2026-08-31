"""Actual Qt component regressions for FS-030 Educational Mode."""

import os
from typing import ClassVar, cast

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from fourier_sketch.application import EducationalStep
from fourier_sketch.ui.desktop import DesktopWindow

pytestmark = pytest.mark.component


class _MemorySettings:
    values: ClassVar[dict[str, object]] = {}

    def __init__(self, *_args: object) -> None:
        pass

    def value(self, key: str, default: object, _type: object) -> object:
        return self.values.get(key, default)

    def setValue(self, key: str, value: object) -> None:
        self.values[key] = value


@pytest.fixture(autouse=True)
def _isolated_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    _MemorySettings.values = {}
    monkeypatch.setattr("fourier_sketch.ui.desktop.QSettings", _MemorySettings)


def _application() -> QApplication:
    return cast(QApplication, QApplication.instance() or QApplication([]))


def _alt_key(key: Qt.Key) -> QKeyEvent:
    return QKeyEvent(
        QEvent.Type.KeyPress,
        key,
        Qt.KeyboardModifier.AltModifier,
    )


def test_lesson_gating_highlights_keyboard_playback_and_locks() -> None:
    app = _application()
    window = DesktopWindow(locale="pseudo")
    window.show()
    window.activateWindow()
    app.processEvents()
    assert not window._educational_action.isEnabled()
    assert not window._educational_next.isEnabled()

    window._educational_load.click()
    assert window._timeline is not None
    assert window._educational_action.isEnabled()
    window._educational_action.click()
    app.processEvents()

    assert window._educational.active
    assert window._educational_snapshot is not None
    assert window._educational_snapshot.step is EducationalStep.SAMPLES
    assert window._canvas.educational_sample is window._educational_snapshot.sample
    assert window._canvas.selected_harmonic_frequency == 1
    assert window._inspector_list.currentItem().data(Qt.ItemDataRole.UserRole) == 1
    assert window._educational_mode.text().startswith("[!! ")
    assert not window._harmonics.isEnabled()
    assert not window._inspector_list.isEnabled()
    assert not window._solo_action.isEnabled()
    assert not window._build_up_action.isEnabled()
    assert not window._export_nav.isEnabled()

    window.keyPressEvent(_alt_key(Qt.Key.Key_Right))
    assert window._educational.step is EducationalStep.COEFFICIENT
    assert window._canvas.educational_sample is None
    window.keyPressEvent(
        QKeyEvent(
            QEvent.Type.KeyPress,
            Qt.Key.Key_Right,
            Qt.KeyboardModifier.NoModifier,
        )
    )
    assert window._educational.step is EducationalStep.COEFFICIENT
    window.keyPressEvent(_alt_key(Qt.Key.Key_Home))
    assert window._educational.step is EducationalStep.SAMPLES

    window._zoom.setFocus()
    zoom_before = window._zoom.value()
    QTest.keyClick(
        window._zoom,
        Qt.Key.Key_Right,
        Qt.KeyboardModifier.AltModifier,
    )
    app.processEvents()
    assert window._educational.step is EducationalStep.COEFFICIENT
    QTest.keyClick(
        window._zoom,
        Qt.Key.Key_Home,
        Qt.KeyboardModifier.AltModifier,
    )
    app.processEvents()
    assert window._educational.step is EducationalStep.SAMPLES
    assert window._zoom.value() == zoom_before

    window._timeline_action("play")
    window._timeline_action("advance", 0.125)
    assert window._educational_snapshot is not None
    assert window._educational_snapshot.latest_trace is window._current_frame.chain.endpoint
    window._timeline_action("pause")

    window._educational_action.click()
    assert not window._educational.active
    assert window._canvas.educational_sample is None
    assert window._harmonics.isEnabled()
    assert window._export_nav.isEnabled()
    window.close()


def test_new_nonlesson_timeline_clears_mode_and_values() -> None:
    _application()
    window = DesktopWindow()
    window._educational_load.click()
    window._educational_action.click()
    assert window._educational.active
    assert window._timeline is not None

    replacement = window._timeline
    window._apply_timeline(replacement)

    assert not window._educational.active
    assert window._educational_lesson is None
    assert not window._educational_action.isEnabled()
    assert window._educational_body.text() == ""
    assert window._educational_equation.text() == ""
    window.close()
