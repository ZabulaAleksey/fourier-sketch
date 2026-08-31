"""Component regressions for the read-only FS-024 desktop inspector."""

import os
from math import cos, pi, sin
from typing import ClassVar, cast

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent
from PySide6.QtWidgets import QApplication

from fourier_sketch.application import EpicycleTimeline, build_freehand_timeline
from fourier_sketch.domain import Curve, Point2D
from fourier_sketch.presentation.harmonic_inspector import (
    build_harmonic_inspector_item,
)
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


def _timeline(*, phase: float = 0.0) -> EpicycleTimeline:
    points = tuple(
        Point2D(
            cos(2.0 * pi * index / 16 + phase)
            + 0.35 * cos(6.0 * pi * index / 16),
            sin(2.0 * pi * index / 16 + phase)
            + 0.35 * sin(6.0 * pi * index / 16),
        )
        for index in range(16)
    )
    return build_freehand_timeline(Curve(points, closed=True), harmonic_count=4)


def _mouse_event(
    event_type: QEvent.Type,
    point: QPointF,
    *,
    button: Qt.MouseButton,
    buttons: Qt.MouseButton,
) -> QMouseEvent:
    return QMouseEvent(
        event_type,
        point,
        point,
        point,
        button,
        buttons,
        Qt.KeyboardModifier.NoModifier,
    )


def _device_point(window: DesktopWindow, point: Point2D) -> QPointF:
    scale, center_x, center_y = window._canvas._scene_transform()
    return QPointF(
        window._canvas.width() / 2.0
        + window._canvas.view_pan[0]
        + (point.x - center_x) * scale,
        window._canvas.height() / 2.0
        + window._canvas.view_pan[1]
        - (point.y - center_y) * scale,
    )


def test_list_keyboard_selection_is_exact_localized_and_presentation_only() -> None:
    app = _application()
    window = DesktopWindow(locale="pseudo")
    assert not window._inspector_list.isEnabled()
    assert window._inspector_message.text().startswith("[!! ")
    timeline = _timeline()
    window._apply_timeline(timeline)
    frame = timeline.snapshot()
    before = timeline.snapshot()

    window._inspector_list.setFocus()
    app.sendEvent(
        window._inspector_list,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Down, Qt.KeyboardModifier.NoModifier),
    )
    selected = window._selected_harmonic_frequency

    assert selected == frame.selection.frequencies[0]
    item = build_harmonic_inspector_item(frame.selection, frame.chain, selected)
    assert item is not None
    assert window._inspector_values["frequency"].text() == str(item.frequency)
    assert window._inspector_values["amplitude"].text() == f"{item.amplitude:.6g}"
    assert window._inspector_values["phase"].text() == f"{item.phase:.6g}"
    assert window._inspector_values["local_value"].text() == (
        f"{item.local_value.real:+.6g} {item.local_value.imag:+.6g}i"
    )
    assert window._canvas.selected_harmonic_frequency == selected
    assert timeline.snapshot() == before

    timeline.play()
    advanced = timeline.advance(0.125)
    window._apply_frame(advanced)
    moved_item = build_harmonic_inspector_item(
        advanced.selection,
        advanced.chain,
        selected,
    )
    assert moved_item is not None
    assert window._selected_harmonic_frequency == selected
    assert window._inspector_values["local_value"].text() == (
        f"{moved_item.local_value.real:+.6g} {moved_item.local_value.imag:+.6g}i"
    )
    window.close()


def test_canvas_vector_circle_click_and_drag_pan_keep_contracts_separate() -> None:
    _application()
    window = DesktopWindow()
    timeline = _timeline()
    window._apply_timeline(timeline)
    window._canvas.resize(640, 480)
    assert window._current_frame is not None
    vector = window._current_frame.chain.vectors[1]
    midpoint = Point2D(
        (vector.start.x + vector.end.x) / 2.0,
        (vector.start.y + vector.end.y) / 2.0,
    )
    vector_point = _device_point(window, midpoint)
    before = timeline.snapshot()

    window._canvas.mousePressEvent(
        _mouse_event(
            QEvent.Type.MouseButtonPress,
            vector_point,
            button=Qt.MouseButton.LeftButton,
            buttons=Qt.MouseButton.LeftButton,
        )
    )
    window._canvas.mouseReleaseEvent(
        _mouse_event(
            QEvent.Type.MouseButtonRelease,
            vector_point,
            button=Qt.MouseButton.LeftButton,
            buttons=Qt.MouseButton.NoButton,
        )
    )
    assert window._selected_harmonic_frequency == vector.frequency
    assert timeline.snapshot() == before

    window._apply_frame(timeline.set_visibility(vectors=False, circles=True))
    assert window._current_frame is not None
    circle_vector = None
    circle_point = None
    circle_scene_point = None
    for candidate_vector in window._current_frame.chain.vectors:
        if candidate_vector.amplitude <= 1e-9:
            continue
        for angle_index in range(16):
            angle = 2.0 * pi * angle_index / 16
            candidate_scene_point = Point2D(
                candidate_vector.start.x + candidate_vector.amplitude * cos(angle),
                candidate_vector.start.y + candidate_vector.amplitude * sin(angle),
            )
            candidate_point = _device_point(window, candidate_scene_point)
            if (
                window._canvas._hit_test_harmonic(candidate_point)
                == candidate_vector.frequency
            ):
                circle_vector = candidate_vector
                circle_point = candidate_point
                circle_scene_point = candidate_scene_point
                break
        if circle_point is not None:
            break
    assert circle_vector is not None
    assert circle_point is not None
    assert circle_scene_point is not None
    window._canvas.mousePressEvent(
        _mouse_event(
            QEvent.Type.MouseButtonPress,
            circle_point,
            button=Qt.MouseButton.LeftButton,
            buttons=Qt.MouseButton.LeftButton,
        )
    )
    window._canvas.mouseReleaseEvent(
        _mouse_event(
            QEvent.Type.MouseButtonRelease,
            circle_point,
            button=Qt.MouseButton.LeftButton,
            buttons=Qt.MouseButton.NoButton,
        )
    )
    assert window._selected_harmonic_frequency == circle_vector.frequency

    selected = window._selected_harmonic_frequency
    pan_before = window._canvas.view_pan
    start = QPointF(100.0, 100.0)
    end = QPointF(140.0, 125.0)
    window._canvas.mousePressEvent(
        _mouse_event(
            QEvent.Type.MouseButtonPress,
            start,
            button=Qt.MouseButton.LeftButton,
            buttons=Qt.MouseButton.LeftButton,
        )
    )
    window._canvas.mouseMoveEvent(
        _mouse_event(
            QEvent.Type.MouseMove,
            end,
            button=Qt.MouseButton.NoButton,
            buttons=Qt.MouseButton.LeftButton,
        )
    )
    window._canvas.mouseReleaseEvent(
        _mouse_event(
            QEvent.Type.MouseButtonRelease,
            end,
            button=Qt.MouseButton.LeftButton,
            buttons=Qt.MouseButton.NoButton,
        )
    )
    assert window._canvas.view_pan != pan_before
    assert window._selected_harmonic_frequency == selected

    window._canvas.set_view_zoom(1.5)
    transformed_circle_point = _device_point(window, circle_scene_point)
    window._canvas.mousePressEvent(
        _mouse_event(
            QEvent.Type.MouseButtonPress,
            transformed_circle_point,
            button=Qt.MouseButton.LeftButton,
            buttons=Qt.MouseButton.LeftButton,
        )
    )
    window._canvas.mouseReleaseEvent(
        _mouse_event(
            QEvent.Type.MouseButtonRelease,
            transformed_circle_point,
            button=Qt.MouseButton.LeftButton,
            buttons=Qt.MouseButton.NoButton,
        )
    )
    assert window._selected_harmonic_frequency == circle_vector.frequency

    off_canvas = QPointF(-1000.0, -1000.0)
    window._canvas.mousePressEvent(
        _mouse_event(
            QEvent.Type.MouseButtonPress,
            off_canvas,
            button=Qt.MouseButton.LeftButton,
            buttons=Qt.MouseButton.LeftButton,
        )
    )
    window._canvas.mouseReleaseEvent(
        _mouse_event(
            QEvent.Type.MouseButtonRelease,
            off_canvas,
            button=Qt.MouseButton.LeftButton,
            buttons=Qt.MouseButton.NoButton,
        )
    )
    assert window._selected_harmonic_frequency is None
    window.close()


def test_harmonic_count_and_new_timeline_clear_only_when_identity_is_stale() -> None:
    _application()
    window = DesktopWindow()
    timeline = _timeline()
    window._apply_timeline(timeline)
    selected = timeline.snapshot().selection.frequencies[2]
    window._select_harmonic(selected)

    window._apply_frame(timeline.set_harmonic_count(6))
    assert window._selected_harmonic_frequency == selected
    window._apply_frame(timeline.set_harmonic_count(2))
    assert window._selected_harmonic_frequency is None
    assert window._inspector_values["frequency"].text() == "—"
    assert "no longer available" in window._inspector_message.text()

    window._select_harmonic(timeline.snapshot().selection.frequencies[0])
    replacement = _timeline(phase=0.25)
    window._apply_timeline(replacement)
    assert window._selected_harmonic_frequency is None
    assert window._inspector_list.currentRow() == -1
    window.close()
