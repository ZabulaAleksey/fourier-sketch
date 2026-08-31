"""Actual Qt canonical-circle Educational Mode E2E for FS-030."""

import os
from typing import ClassVar, cast

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from fourier_sketch.application import EducationalStep, TimelineState
from fourier_sketch.ui.desktop import DesktopWindow

pytestmark = pytest.mark.e2e


class _MemorySettings:
    values: ClassVar[dict[str, object]] = {}

    def __init__(self, *_args: object) -> None:
        pass

    def value(self, key: str, default: object, _type: object) -> object:
        return self.values.get(key, default)

    def setValue(self, key: str, value: object) -> None:
        self.values[key] = value


def test_load_circle_step_actual_animation_pause_and_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("fourier_sketch.ui.desktop.QSettings", _MemorySettings)
    app = cast(QApplication, QApplication.instance() or QApplication([]))
    window = DesktopWindow()

    window._educational_load.click()
    window._educational_action.click()
    assert window._timeline is not None
    assert window._timeline.state is TimelineState.PAUSED

    for expected in tuple(EducationalStep)[1:]:
        window._educational_next.click()
        app.processEvents()
        assert window._educational_snapshot is not None
        assert window._current_frame is not None
        assert window._educational_snapshot.step is expected
        assert window._educational_snapshot.latest_trace is window._current_frame.chain.endpoint

    window._timeline_action("play")
    window._timeline_action("advance", 0.1)
    window._timeline_action("pause")
    assert window._educational_snapshot is not None
    assert window._current_frame is not None
    assert window._educational_snapshot.trace_count >= 2
    assert window._educational_snapshot.latest_trace is window._current_frame.chain.endpoint

    window._educational_action.click()
    assert not window._educational.active
    assert window._current_frame == window._timeline.snapshot()
    window.close()
