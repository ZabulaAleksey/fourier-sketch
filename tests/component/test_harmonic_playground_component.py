"""Actual Qt component regressions for the FS-033 harmonic playground."""

import os
from typing import ClassVar, cast

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from fourier_sketch.application import TimelineState, build_basis_timeline
from fourier_sketch.domain import BasisKind, Curve, Point2D
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


def _curve() -> Curve:
    return Curve(
        (
            Point2D(-2.0, 0.0),
            Point2D(-1.0, 1.0),
            Point2D(0.0, -0.5),
            Point2D(1.0, 1.5),
            Point2D(2.0, 0.0),
        ),
        closed=False,
    )


def test_playground_authors_real_fourier_chain_and_restores_baseline() -> None:
    _application()
    window = DesktopWindow()
    baseline = build_basis_timeline(
        _curve(), basis=BasisKind.FOURIER_EPICYCLE, speed=0.25
    )
    window._apply_basis_timeline(baseline, reference_view_size=(600.0, 400.0))
    window._canvas.restore_view_state(2.0, (17.0, -11.0), (600.0, 400.0))
    baseline_frame = baseline.snapshot()

    window._toggle_playground()

    assert window._playground_active
    assert tuple(item.frequency for item in window._playground.components) == (1,)
    assert window._timeline is not baseline
    assert window._timeline is not None
    assert window._timeline.snapshot().selection.frequencies == (1,)
    assert not window._timeline.snapshot().visibility.original
    assert window._canvas._frame is not None
    assert window._canvas._frame.chain.endpoint == Point2D(1.0, 0.0)
    assert not window._source.isEnabled()
    assert not window._basis_selector.isEnabled()
    assert not window._harmonics.isEnabled()
    assert not window._solo_action.isEnabled()
    assert not window._build_up_action.isEnabled()
    assert not window._educational_action.isEnabled()
    assert not window._export_nav.isEnabled()
    assert not window._visibility_toggles["original"].isEnabled()

    window._playground_frequency.setValue(-2)
    window._playground_amplitude.setValue(0.35)
    window._playground_phase.setValue(45.0)
    window._apply_playground_component()

    assert tuple(item.frequency for item in window._playground.components) == (1, -2)
    assert window._timeline is not None
    authored = window._timeline.snapshot()
    assert authored.selection.frequencies == (1, -2)
    assert authored.timeline_state is TimelineState.PAUSED
    assert len(authored.trace) == 1
    assert window._inspector_list.isEnabled()
    assert window._inspector_list.count() == 2
    assert "k=-2" in window._inspector_list.item(1).text()
    assert window._canvas.view_zoom == 2.0
    assert window._canvas.view_pan == (17.0, -11.0)

    window._timeline_action("play")
    window._timeline_action("advance", 0.1)
    assert window._timeline.snapshot().timeline_state is TimelineState.RUNNING
    assert len(window._timeline.snapshot().trace) == 2

    window._toggle_playground()

    assert not window._playground_active
    assert window._timeline is baseline
    restored = baseline.snapshot()
    assert restored.selection == baseline_frame.selection
    assert restored.trace == baseline_frame.trace
    assert restored.speed == baseline_frame.speed
    assert restored.timeline_state is baseline_frame.timeline_state
    assert window._canvas.view_zoom == 2.0
    assert window._canvas.view_pan == (17.0, -11.0)
    assert window._canvas.reference_view_size == (600.0, 400.0)
    assert window._source.isEnabled()
    window.close()


def test_playground_rejects_total_amplitude_transactionally() -> None:
    _application()
    window = DesktopWindow()
    window._toggle_playground()
    window._playground_amplitude.setValue(4.0)
    window._apply_playground_component()

    window._playground_frequency.setValue(2)
    window._playground_amplitude.setValue(4.0)
    window._apply_playground_component()
    before = window._playground.components

    window._playground_frequency.setValue(3)
    window._playground_amplitude.setValue(0.01)
    window._apply_playground_component()

    assert window._playground.components == before
    assert window._status.text() == window._translator.text(
        "desktop.playground.invalid"
    )
    window.close()


def test_playground_temporarily_identifies_fourier_and_restores_indexed_view() -> None:
    _application()
    window = DesktopWindow()
    basis = BasisKind.DCT_II
    window._basis_selector.setCurrentIndex(
        window._basis_selector.findData(basis.value)
    )
    baseline = build_basis_timeline(_curve(), basis=basis, speed=0.5)
    window._apply_basis_timeline(baseline, reference_view_size=(500.0, 300.0))
    window._visibility_toggles["original"].setChecked(False)
    assert not window._canvas._haar_visibility["original"]

    window._toggle_playground()

    assert window._selected_basis() is BasisKind.FOURIER_EPICYCLE
    assert window._timeline is not None
    assert window._canvas._frame is not None

    window._toggle_playground()

    assert window._selected_basis() is basis
    assert window._indexed_timeline is baseline
    assert window._canvas._indexed_frame is not None
    assert not window._visibility_toggles["original"].isChecked()
    assert not window._canvas._haar_visibility["original"]
    window.close()
