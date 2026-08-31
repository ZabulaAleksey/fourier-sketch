"""Qt component regressions for the bounded FS-026 Build-Up mode."""

import os
from math import cos, pi, sin
from typing import ClassVar, cast

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from fourier_sketch.application import BuildUpState, EpicycleTimeline, build_freehand_timeline
from fourier_sketch.domain import Curve, Point2D, SpectrumOrdering
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


def _timeline() -> EpicycleTimeline:
    points = tuple(
        Point2D(
            cos(2.0 * pi * index / 16) + 0.35 * cos(6.0 * pi * index / 16),
            sin(2.0 * pi * index / 16) + 0.35 * sin(6.0 * pi * index / 16),
        )
        for index in range(16)
    )
    return build_freehand_timeline(Curve(points, closed=True), harmonic_count=4)


def test_build_up_controls_project_each_k_and_restore_exact_baseline() -> None:
    app = _application()
    window = DesktopWindow(locale="pseudo")
    timeline = _timeline()
    window._apply_timeline(timeline)
    baseline = window._baseline_frame
    assert baseline is not None
    window._inspector_list.setCurrentRow(1)
    restore_frequency = window._selected_harmonic_frequency
    ordering_index = window._build_up_ordering.findData(
        SpectrumOrdering.INTERLEAVED.value
    )
    assert ordering_index >= 0
    window._build_up_ordering.setCurrentIndex(ordering_index)
    window._build_up_target.setValue(3)
    window._build_up_dwell.setValue(100)

    assert window._build_up_action.accessibleName()
    window._build_up_action.click()
    app.processEvents()

    assert window._build_up.active
    assert window._build_up.state is BuildUpState.RUNNING
    assert window._build_up_snapshot is not None
    assert window._build_up_snapshot.metrics.current_count == 1
    assert window._build_up_mode.text().startswith("[!! ")
    assert window._current_frame is window._build_up_snapshot.frame
    assert len(window._current_frame.selection.coefficients) == 1
    assert window._current_frame.trace == (window._current_frame.chain.endpoint,)
    assert not window._harmonics.isEnabled()
    assert not window._speed.isEnabled()
    assert not window._inspector_list.isEnabled()
    assert not window._solo_action.isEnabled()
    assert not window._export_nav.isEnabled()
    assert not window._export_action.isEnabled()
    assert all(not toggle.isEnabled() for toggle in window._visibility_toggles.values())
    assert timeline.snapshot() == baseline

    window._timeline_action("harmonics", 1)
    window._timeline_action("advance", 0.1)
    assert window._build_up_snapshot is not None
    assert window._build_up_snapshot.metrics.current_count == 2
    assert len(window._current_frame.selection.coefficients) == 2
    assert window._current_frame.trace == (window._current_frame.chain.endpoint,)
    assert timeline.snapshot() == baseline

    window._timeline_action("pause")
    window._timeline_action("advance", 1.0)
    assert window._build_up.current_count == 2
    window._timeline_action("restart")
    assert window._build_up.state is BuildUpState.PAUSED
    assert window._build_up_snapshot is not None
    assert window._build_up_snapshot.metrics.current_count == 1
    assert window._current_frame.trace == (window._current_frame.chain.endpoint,)

    window._timeline_action("play")
    window._timeline_action("advance", 0.1)
    window._timeline_action("advance", 0.1)
    assert window._build_up.state is BuildUpState.COMPLETED
    assert window._build_up_snapshot is not None
    assert window._build_up_snapshot.metrics.current_count == 3
    assert not window._timer.isActive()
    assert timeline.snapshot() == baseline

    window._build_up_action.click()
    app.processEvents()
    assert not window._build_up.active
    assert window._current_frame is baseline
    assert window._selected_harmonic_frequency == restore_frequency
    assert window._harmonics.isEnabled()
    assert window._speed.isEnabled()
    assert window._export_nav.isEnabled()
    assert timeline.snapshot() == baseline
    window.close()


def test_exit_resumes_running_baseline_without_catch_up() -> None:
    _application()
    window = DesktopWindow()
    timeline = _timeline()
    window._apply_timeline(timeline)
    window._timeline_action("play")
    baseline = window._baseline_frame
    assert baseline is not None
    assert window._timer.isActive()
    window._build_up_target.setValue(2)

    window._build_up_action.click()
    window._timeline_action("advance", 0.5)
    assert timeline.snapshot() == baseline
    window._build_up_action.click()

    assert window._current_frame is baseline
    assert timeline.snapshot() == baseline
    assert window._timer.isActive()
    window._timer.stop()
    window.close()
