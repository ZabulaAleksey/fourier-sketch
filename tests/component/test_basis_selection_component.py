"""Actual Qt component regressions for FS-032 basis-specific desktop behavior."""

import os
import time
from types import SimpleNamespace
from typing import ClassVar, cast

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from fourier_sketch.application import HaarTimeline, TimelineState, build_basis_timeline
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


def test_default_fourier_selection_preserves_existing_frame_and_clear_contract() -> None:
    _application()
    window = DesktopWindow()
    assert window._selected_basis() is BasisKind.FOURIER_EPICYCLE

    timeline = build_basis_timeline(_curve(), basis=BasisKind.FOURIER_EPICYCLE)
    window._apply_basis_timeline(timeline, reference_view_size=(600.0, 400.0))

    assert window._timeline is timeline
    assert window._haar_timeline is None
    assert window._canvas._frame is not None
    assert window._canvas._haar_frame is None
    assert not window._basis_selector.isEnabled()
    assert window._term_label.text() == window._translator.text("control.harmonics")

    window._reset_source()
    assert window._timeline is None
    assert window._canvas._frame is None
    assert window._basis_selector.isEnabled()
    window.close()


def test_haar_view_uses_terms_without_fourier_geometry_and_keeps_view_controls() -> None:
    _application()
    window = DesktopWindow(locale="pseudo")
    index = window._basis_selector.findData(BasisKind.HAAR_WAVELET.value)
    window._basis_selector.setCurrentIndex(index)
    assert window._selected_basis() is BasisKind.HAAR_WAVELET
    assert not window._image_button.isEnabled()

    timeline = build_basis_timeline(
        _curve(),
        basis=BasisKind.HAAR_WAVELET,
        speed=1.0,
    )
    assert isinstance(timeline, HaarTimeline)
    window._apply_basis_timeline(timeline, reference_view_size=(600.0, 400.0))

    frame = window._canvas._haar_frame
    assert frame is not None
    assert frame.source is timeline.source
    assert frame.analysis is timeline.analysis
    assert window._canvas._frame is None
    assert not window._canvas._circle_centers
    assert not window._canvas._vector_lines
    assert window._canvas.accessibleName().startswith("[!! ")
    assert window._term_label.text().startswith("[!! ")
    assert window._harmonics.maximum() == 128
    assert not window._inspector_list.isEnabled()
    assert not window._solo_action.isEnabled()
    assert not window._build_up_action.isEnabled()
    assert not window._educational_action.isEnabled()
    assert not window._export_nav.isEnabled()
    assert window._visibility_toggles["original"].isEnabled()
    assert window._visibility_toggles["reconstruction"].isEnabled()
    assert not window._visibility_toggles["circles"].isEnabled()

    source = frame.source
    analysis = frame.analysis
    window._harmonics.setValue(3)
    assert window._canvas._haar_frame is not None
    assert window._canvas._haar_frame.term_count == 3
    window._timeline_action("restart")
    assert window._canvas._haar_frame is not None
    assert window._canvas._haar_frame.term_count == 1
    assert window._canvas._haar_frame.state is TimelineState.PAUSED
    window._timeline_action("play")
    window._visibility_toggles["original"].setChecked(False)
    window._timeline_action("advance", 0.25)
    assert window._canvas._haar_frame is not None
    assert window._canvas._haar_frame.term_count == 2
    assert window._canvas._haar_frame.source is source
    assert window._canvas._haar_frame.analysis is analysis
    assert not window._visibility_toggles["original"].isChecked()
    assert not window._canvas._haar_visibility["original"]

    zoom_before = window._canvas.view_zoom
    window._canvas.set_view_zoom(2.0)
    assert window._canvas.view_zoom != zoom_before
    assert timeline.source is source
    assert timeline.analysis is analysis
    window.close()


def test_haar_completion_pauses_and_selected_basis_survives_error_or_restart() -> None:
    _application()
    window = DesktopWindow()
    index = window._basis_selector.findData(BasisKind.HAAR_WAVELET.value)
    window._basis_selector.setCurrentIndex(index)
    timeline = build_basis_timeline(_curve(), basis=BasisKind.HAAR_WAVELET, speed=1.0)
    assert isinstance(timeline, HaarTimeline)
    window._apply_basis_timeline(timeline)

    window._harmonics.setValue(timeline.maximum_terms)
    window._timeline_action("play")
    assert timeline.state is TimelineState.PAUSED
    window._timeline_action("restart")
    assert timeline.term_count == 1
    assert window._selected_basis() is BasisKind.HAAR_WAVELET

    window._build_freehand(
        SimpleNamespace(points=(Point2D(0.0, 0.0), Point2D(0.0, 0.0)))
    )
    assert window._timeline is None
    assert window._haar_timeline is None
    assert window._canvas._frame is None
    assert window._canvas._haar_frame is None
    app = _application()
    deadline = time.monotonic() + 3.0
    while window._job is not None and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)
    assert window._job is None
    assert window._selected_basis() is BasisKind.HAAR_WAVELET
    assert window._timeline is None
    assert window._haar_timeline is None
    assert window._status.text() == window._translator.text("basis.haar.invalid")
    window.close()


def test_background_result_keeps_selector_locked_to_displayed_basis() -> None:
    app = _application()
    window = DesktopWindow()
    timeline = build_basis_timeline(_curve(), basis=BasisKind.FOURIER_EPICYCLE)

    def delayed_result() -> object:
        time.sleep(0.05)
        return timeline

    window._start_job(delayed_result, window._apply_basis_timeline)
    assert not window._basis_selector.isEnabled()
    deadline = time.monotonic() + 3.0
    while window._job is not None and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)

    assert window._job is None
    assert window._timeline is timeline
    assert window._selected_basis() is BasisKind.FOURIER_EPICYCLE
    assert not window._basis_selector.isEnabled()
    window.close()
