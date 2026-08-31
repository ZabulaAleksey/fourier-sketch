"""Responsive PySide6 shell that only dispatches existing application use cases."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from math import hypot, isfinite
from pathlib import Path
from time import monotonic
from typing import cast

from PySide6.QtCore import QEvent, QLineF, QPointF, QSettings, Qt, QThread, QTimer, Signal
from PySide6.QtGui import (
    QCloseEvent,
    QColor,
    QEventPoint,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
    QTouchEvent,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from fourier_sketch.application import (
    AnimationExportPlan,
    CaptureState,
    EpicycleFrame,
    EpicycleTimeline,
    ExportFormat,
    FreehandCapture,
    ImageMvpConfig,
    ImageMvpController,
    ImageMvpSnapshot,
    ImageMvpState,
    TimelineState,
    build_freehand_timeline,
    export_coefficient_data,
    export_curve_data,
    mp4_capability,
    safe_display_basename,
    validate_local_path,
)
from fourier_sketch.domain import Curve, DomainValidationError, Point2D
from fourier_sketch.imaging import ImagePreprocessingOptions
from fourier_sketch.presentation import Translator, resolve_locale
from fourier_sketch.presentation.harmonic_inspector import (
    HarmonicInspectorItem,
    build_harmonic_inspector_item,
)
from fourier_sketch.render import export_animation_gif, render_frame_png, render_spectrum_png


class _Job(QThread):
    """One bounded worker; it publishes only completed application snapshots."""

    finished_snapshot = Signal(object)
    failed = Signal(str)
    progress = Signal(int)

    def __init__(self, operation: Callable[[], object]) -> None:
        super().__init__()
        self._operation = operation

    def run(self) -> None:
        try:
            result = self._operation()
            if self.isInterruptionRequested():
                return
            self.finished_snapshot.emit(result)
        except Exception:
            self.failed.emit("desktop.error.runtime")


_SPEED_MIN = 0.01
_SPEED_MAX = 1.00
_SPEED_STEP = 0.01
_SPEED_SCALE = int(1 / _SPEED_STEP)
_SPEED_SETTINGS_VERSION = 2
_VIEW_ZOOM_MIN = 0.01
_VIEW_ZOOM_MAX = 100.00
_VIEW_ZOOM_SCALE = 100
_VIEW_ZOOM_DEFAULT = 1.00
_SOURCE_LAYOUT_BOTTOM_RESERVE = 250
_RAINBOW_HUE_STEP = 0.618033988749895
_HARMONIC_HIT_TOLERANCE = 8.0


@dataclass(frozen=True, slots=True)
class _DevicePoint:
    x: float
    y: float


def _point_to_segment_distance(
    point: _DevicePoint,
    start: _DevicePoint,
    end: _DevicePoint,
) -> float:
    """Return the shortest device-pixel distance to a finite segment."""

    delta_x = end.x - start.x
    delta_y = end.y - start.y
    length_squared = delta_x * delta_x + delta_y * delta_y
    if length_squared <= 1e-12:
        return hypot(point.x - start.x, point.y - start.y)
    projection = (
        (point.x - start.x) * delta_x + (point.y - start.y) * delta_y
    ) / length_squared
    bounded = max(0.0, min(1.0, projection))
    nearest_x = start.x + bounded * delta_x
    nearest_y = start.y + bounded * delta_y
    return hypot(point.x - nearest_x, point.y - nearest_y)


def _export_dialog_contract(export_format: ExportFormat) -> tuple[str, str]:
    contracts = {
        ExportFormat.CURVE_JSON: (".json", "desktop.export.filter.json"),
        ExportFormat.CURVE_CSV: (".csv", "desktop.export.filter.csv"),
        ExportFormat.COEFFICIENTS_JSON: (".json", "desktop.export.filter.json"),
        ExportFormat.COEFFICIENTS_CSV: (".csv", "desktop.export.filter.csv"),
        ExportFormat.RECONSTRUCTION_PNG: (".png", "desktop.export.filter.png"),
        ExportFormat.SPECTRUM_PNG: (".png", "desktop.export.filter.png"),
        ExportFormat.GIF: (".gif", "desktop.export.filter.gif"),
    }
    try:
        return contracts[export_format]
    except KeyError as error:
        raise DomainValidationError("selected export format has no file contract") from error


def _rainbow_color(selection_index: int) -> QColor:
    """Return a stable presentation color independent of the selected K."""

    hue = (selection_index * _RAINBOW_HUE_STEP) % 1.0
    return QColor.fromHsvF(hue, 0.78, 0.90)


def _bounded_view_zoom(zoom: float) -> float:
    if not isfinite(zoom):
        raise ValueError("view zoom must be finite")
    bounded = max(_VIEW_ZOOM_MIN, min(_VIEW_ZOOM_MAX, zoom))
    return round(bounded * _VIEW_ZOOM_SCALE) / _VIEW_ZOOM_SCALE


def _center_anchored_view_transform(
    *,
    zoom: float,
    pan: tuple[float, float],
    requested_zoom: float,
) -> tuple[float, tuple[float, float]]:
    """Keep the scene-coordinate under the geometric viewport center unchanged."""

    next_zoom = _bounded_view_zoom(requested_zoom)
    if next_zoom == zoom:
        return zoom, pan
    scale_ratio = next_zoom / zoom
    return next_zoom, (pan[0] * scale_ratio, pan[1] * scale_ratio)


def _gesture_view_transform(
    *,
    zoom: float,
    pan: tuple[float, float],
    previous_points: tuple[tuple[float, float], ...],
    current_points: tuple[tuple[float, float], ...],
) -> tuple[float, tuple[float, float]]:
    """Compute one-finger pan or fixed-center two-finger zoom without product state."""

    if len(previous_points) != len(current_points):
        return zoom, pan
    if len(current_points) == 1:
        return zoom, (
            pan[0] + current_points[0][0] - previous_points[0][0],
            pan[1] + current_points[0][1] - previous_points[0][1],
        )
    if len(current_points) != 2:
        return zoom, pan

    previous_dx = previous_points[1][0] - previous_points[0][0]
    previous_dy = previous_points[1][1] - previous_points[0][1]
    current_dx = current_points[1][0] - current_points[0][0]
    current_dy = current_points[1][1] - current_points[0][1]
    previous_distance = (previous_dx * previous_dx + previous_dy * previous_dy) ** 0.5
    current_distance = (current_dx * current_dx + current_dy * current_dy) ** 0.5

    if previous_distance <= 1e-9:
        return zoom, pan
    return _center_anchored_view_transform(
        zoom=zoom,
        pan=pan,
        requested_zoom=zoom * current_distance / previous_distance,
    )


class EpicycleCanvas(QWidget):
    """Paint-only view of a ready immutable frame; it never calculates Fourier state."""

    view_zoom_changed = Signal(float)
    harmonic_selected = Signal(object)

    def __init__(self, translator: Translator, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._translator = translator
        self._frame: EpicycleFrame | None = None
        self._frame_cache_key: tuple[int, int, tuple[int, ...]] | None = None
        self._scene_bounds: tuple[float, float, float, float] | None = None
        self._reference_view_size: tuple[float, float] | None = None
        self._original_scene_path = QPainterPath()
        self._reconstruction_scene_path = QPainterPath()
        self._vector_lines: list[QLineF] = []
        self._circle_centers: list[tuple[float, float, float]] = []
        self._vector_colors: list[QColor] = []
        self._circle_colors: list[QColor] = []
        self._view_zoom = _VIEW_ZOOM_DEFAULT
        self._view_pan = QPointF()
        self._pan_anchor: QPointF | None = None
        self._pan_origin = QPointF()
        self._pan_dragged = False
        self._touch_points: dict[int, tuple[float, float]] = {}
        self._selected_harmonic_frequency: int | None = None
        self.setMinimumSize(360, 300)
        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents)
        self.setAccessibleName("Epicycles canvas")

    @property
    def view_zoom(self) -> float:
        """Return the user-selected view-only scale without touching timeline state."""

        return self._view_zoom

    @property
    def view_pan(self) -> tuple[float, float]:
        """Return the viewport translation in device pixels for component assertions."""

        return (self._view_pan.x(), self._view_pan.y())

    @property
    def selected_harmonic_frequency(self) -> int | None:
        """Return the presentation-only signed frequency highlighted on the canvas."""

        return self._selected_harmonic_frequency

    def set_selected_harmonic(self, frequency: int | None) -> None:
        """Highlight one currently visible harmonic without touching frame state."""

        frame = self._frame
        selected = frequency
        if selected is not None and (
            frame is None or selected not in frame.selection.frequencies
        ):
            selected = None
        if selected == self._selected_harmonic_frequency:
            return
        self._selected_harmonic_frequency = selected
        self.update()

    def set_view_zoom(self, zoom: float) -> None:
        """Set a bounded view scale; rendering remains independent from Fourier state."""

        next_zoom, next_pan = _center_anchored_view_transform(
            zoom=self._view_zoom,
            pan=self.view_pan,
            requested_zoom=zoom,
        )
        if next_zoom == self._view_zoom:
            return
        self._view_zoom = next_zoom
        self._view_pan = QPointF(*next_pan)
        self.update()
        self.view_zoom_changed.emit(self._view_zoom)

    def set_reference_view_size(self, size: tuple[float, float] | None) -> None:
        """Set the source-field extent represented by the fixed-center 1.00x baseline."""

        if size is None:
            self._reference_view_size = None
        else:
            width, height = size
            if not isfinite(width) or not isfinite(height) or width <= 0.0 or height <= 0.0:
                raise DomainValidationError(
                    "reference view size must contain positive finite values"
                )
            self._reference_view_size = (float(width), float(height))
        self.update()

    def reset_view(self) -> None:
        """Restore the fixed-center 1.00x baseline selected for a new desktop view."""

        zoom_changed = self._view_zoom != _VIEW_ZOOM_DEFAULT
        self._view_zoom = _VIEW_ZOOM_DEFAULT
        self._view_pan = QPointF()
        self._pan_anchor = None
        self._pan_origin = QPointF()
        self._pan_dragged = False
        self._touch_points = {}
        self.update()
        if zoom_changed:
            self.view_zoom_changed.emit(self._view_zoom)

    def event(self, event: QEvent) -> bool:
        if event.type() in {
            QEvent.Type.TouchBegin,
            QEvent.Type.TouchUpdate,
            QEvent.Type.TouchEnd,
            QEvent.Type.TouchCancel,
        } and isinstance(event, QTouchEvent):
            self._handle_touch_event(event)
            return True
        return super().event(event)

    def _handle_touch_event(self, event: QTouchEvent) -> None:
        if event.type() in {QEvent.Type.TouchEnd, QEvent.Type.TouchCancel}:
            self._touch_points = {}
            event.accept()
            return

        current_points = {
            point.id(): (point.position().x(), point.position().y())
            for point in event.points()
            if point.state() != QEventPoint.State.Released
        }
        if event.type() == QEvent.Type.TouchBegin:
            self._pan_anchor = None
        self._apply_touch_points(self._touch_points, current_points)
        self._touch_points = current_points
        event.accept()

    def _apply_touch_points(
        self,
        previous: dict[int, tuple[float, float]],
        current: dict[int, tuple[float, float]],
    ) -> None:
        """Apply a testable touch sample transition to presentation state only."""

        if set(previous) != set(current) or len(current) not in {1, 2}:
            return
        point_ids = sorted(current)
        next_zoom, next_pan = _gesture_view_transform(
            zoom=self._view_zoom,
            pan=self.view_pan,
            previous_points=tuple(previous[point_id] for point_id in point_ids),
            current_points=tuple(current[point_id] for point_id in point_ids),
        )
        zoom_changed = next_zoom != self._view_zoom
        pan_changed = next_pan != self.view_pan
        if not zoom_changed and not pan_changed:
            return
        self._view_zoom = next_zoom
        self._view_pan = QPointF(*next_pan)
        self.update()
        if zoom_changed:
            self.view_zoom_changed.emit(self._view_zoom)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() is Qt.MouseButton.LeftButton:
            self._pan_anchor = event.position()
            self._pan_origin = QPointF(self._view_pan)
            self._pan_dragged = False
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._pan_anchor is not None and event.buttons() & Qt.MouseButton.LeftButton:
            position = event.position()
            delta = position - self._pan_anchor
            if not self._pan_dragged:
                self._pan_dragged = (
                    abs(delta.x()) + abs(delta.y()) >= QApplication.startDragDistance()
                )
            if self._pan_dragged:
                self._view_pan = QPointF(
                    self._pan_origin.x() + delta.x(),
                    self._pan_origin.y() + delta.y(),
                )
                self.update()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() is Qt.MouseButton.LeftButton and self._pan_anchor is not None:
            if not self._pan_dragged:
                self.harmonic_selected.emit(self._hit_test_harmonic(event.position()))
            self._pan_anchor = None
            self._pan_origin = QPointF()
            self._pan_dragged = False
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        wheel_delta = event.angleDelta().y()
        if wheel_delta == 0:
            event.ignore()
            return
        zoom_factor = 1.15 ** (wheel_delta / 120.0)
        self.set_view_zoom(self._view_zoom * zoom_factor)
        event.accept()

    def set_frame(self, frame: EpicycleFrame | None) -> None:
        if frame is not None:
            cache_key = (
                id(frame.original),
                id(frame.reconstruction),
                tuple(frame.selection.frequencies),
            )
            if cache_key != self._frame_cache_key:
                self._frame_cache_key = cache_key
                total_amplitude = sum(vector.amplitude for vector in frame.chain.vectors)
                original_points = frame.original.points + (
                    (frame.original.start,) if frame.original.closed else ()
                )
                reconstruction_points = frame.reconstruction.points + (
                    (frame.reconstruction.start,) if frame.reconstruction.closed else ()
                )
                self._original_scene_path, original_bounds = self._build_scene_path(original_points)
                self._reconstruction_scene_path, reconstruction_bounds = self._build_scene_path(
                    reconstruction_points
                )
                minimum_x = min(
                    original_bounds[0],
                    reconstruction_bounds[0],
                    frame.chain.origin.x,
                    frame.chain.origin.x - total_amplitude,
                )
                maximum_x = max(
                    original_bounds[1],
                    reconstruction_bounds[1],
                    frame.chain.origin.x,
                    frame.chain.origin.x + total_amplitude,
                )
                minimum_y = min(
                    original_bounds[2],
                    reconstruction_bounds[2],
                    frame.chain.origin.y,
                    frame.chain.origin.y - total_amplitude,
                )
                maximum_y = max(
                    original_bounds[3],
                    reconstruction_bounds[3],
                    frame.chain.origin.y,
                    frame.chain.origin.y + total_amplitude,
                )
                self._scene_bounds = (minimum_x, maximum_x, minimum_y, maximum_y)
                vector_count = len(frame.chain.vectors)
                self._vector_colors = [_rainbow_color(index) for index in range(vector_count)]
                self._circle_colors = [QColor(color) for color in self._vector_colors]

        if frame is None:
            self._frame_cache_key = None
            self._scene_bounds = None
            self._original_scene_path = QPainterPath()
            self._reconstruction_scene_path = QPainterPath()
            self._vector_lines = []
            self._circle_centers = []
            self._vector_colors = []
            self._circle_colors = []
            self._selected_harmonic_frequency = None
        else:
            self._vector_lines = []
            self._circle_centers = []
            for vector in frame.chain.vectors:
                self._vector_lines.append(
                    QLineF(
                        QPointF(vector.start.x, vector.start.y),
                        QPointF(vector.end.x, vector.end.y),
                    )
                )
                self._circle_centers.append(
                    (vector.start.x, vector.start.y, vector.amplitude),
                )
            if self._selected_harmonic_frequency not in frame.selection.frequencies:
                self._selected_harmonic_frequency = None
        self._frame = frame
        self.update()

    def _build_scene_path(
        self, points: tuple[Point2D, ...]
    ) -> tuple[QPainterPath, tuple[float, float, float, float]]:
        if len(points) < 2:
            return QPainterPath(), (0.0, 0.0, 0.0, 0.0)
        first = points[0]
        minimum_x = first.x
        maximum_x = first.x
        minimum_y = first.y
        maximum_y = first.y
        path = QPainterPath(QPointF(first.x, first.y))
        for point in points[1:]:
            path.lineTo(point.x, point.y)
            minimum_x = min(minimum_x, point.x)
            maximum_x = max(maximum_x, point.x)
            minimum_y = min(minimum_y, point.y)
            maximum_y = max(maximum_y, point.y)
        return path, (minimum_x, maximum_x, minimum_y, maximum_y)

    def paintEvent(self, _event: object) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#f8fafc"))
        frame = self._frame
        if frame is None:
            painter.setPen(QColor("#4b5563"))
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                self._translator.text("desktop.canvas.empty"),
            )
            return
        scene_bounds = self._scene_bounds
        if scene_bounds is None:
            return
        scale, center_x, center_y = self._scene_transform()
        line_scale = 1.0 / scale

        def map_point(point: Point2D) -> QPointF:
            return QPointF(point.x, point.y)

        painter.save()
        painter.translate(
            self.width() / 2.0 + self._view_pan.x(),
            self.height() / 2.0 + self._view_pan.y(),
        )
        painter.scale(scale, -scale)
        painter.translate(-center_x, -center_y)

        # The desktop view does not render or scan the accumulated trace. Static
        # contours plus current chain geometry are sufficient to fit the scene.
        # Cached scene-paths are reused until curves, selection, or resize changes.

        def draw_path(path: QPainterPath, color: str, width: float) -> None:
            painter.setPen(QPen(QColor(color), width * line_scale))
            painter.drawPath(path)

        visibility = frame.visibility
        if visibility.original:
            draw_path(self._original_scene_path, "#94a3b8", 1.0)
        if visibility.reconstruction:
            draw_path(self._reconstruction_scene_path, "#14b8a6", 1.4)
        # Desktop intentionally shows the source and moving endpoint only; the
        # application trace remains available for export and other renderers.
        painter.setBrush(Qt.BrushStyle.NoBrush)
        if visibility.circles:
            for index, ((x, y, radius), color) in enumerate(
                zip(self._circle_centers, self._circle_colors, strict=True)
            ):
                selected = (
                    frame.chain.vectors[index].frequency
                    == self._selected_harmonic_frequency
                )
                painter.setPen(QPen(color, (2.8 if selected else 1.0) * line_scale))
                painter.drawEllipse(QPointF(x, y), radius, radius)
        if visibility.vectors:
            for index, (line, color) in enumerate(
                zip(self._vector_lines, self._vector_colors, strict=True)
            ):
                selected = (
                    frame.chain.vectors[index].frequency
                    == self._selected_harmonic_frequency
                )
                painter.setPen(QPen(color, (3.0 if selected else 1.2) * line_scale))
                painter.drawLine(line)
        if visibility.endpoint:
            painter.setBrush(QColor("#dc2626"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(map_point(frame.chain.endpoint), 4.0 * line_scale, 4.0 * line_scale)
        painter.restore()

    def _hit_test_harmonic(self, point: QPointF) -> int | None:
        """Return the nearest visible harmonic in device pixels, deterministically."""

        frame = self._frame
        if frame is None:
            return None
        scale, center_x, center_y = self._scene_transform()
        target = _DevicePoint(point.x(), point.y())

        def device_point(scene_point: Point2D) -> _DevicePoint:
            return _DevicePoint(
                self.width() / 2.0
                + self._view_pan.x()
                + (scene_point.x - center_x) * scale,
                self.height() / 2.0
                + self._view_pan.y()
                - (scene_point.y - center_y) * scale,
            )

        best: tuple[float, int, int] | None = None
        for index, vector in enumerate(frame.chain.vectors):
            distances: list[float] = []
            if frame.visibility.vectors:
                distances.append(
                    _point_to_segment_distance(
                        target,
                        device_point(vector.start),
                        device_point(vector.end),
                    )
                )
            if frame.visibility.circles:
                center = device_point(vector.start)
                radius = vector.amplitude * scale
                distances.append(
                    abs(hypot(target.x - center.x, target.y - center.y) - radius)
                )
            if not distances:
                continue
            candidate = (min(distances), index, vector.frequency)
            if candidate[0] <= _HARMONIC_HIT_TOLERANCE and (
                best is None or candidate[:2] < best[:2]
            ):
                best = candidate
        return None if best is None else best[2]

    def _scene_transform(self) -> tuple[float, float, float]:
        """Return device scale and fixed scene center for the current presentation baseline."""

        scene_bounds = self._scene_bounds
        if scene_bounds is None:
            return (max(self._view_zoom, 1e-12), 0.0, 0.0)
        reference_size = self._reference_view_size
        if reference_size is not None:
            base_scale = min(
                self.width() / reference_size[0],
                self.height() / reference_size[1],
            )
            return (max(base_scale * self._view_zoom, 1e-12), 0.0, 0.0)
        minimum_x, maximum_x, minimum_y, maximum_y = scene_bounds
        span = max(maximum_x - minimum_x, maximum_y - minimum_y, 1.0) * 1.15
        scale = min(self.width(), self.height()) / span * self._view_zoom
        return (
            max(scale, 1e-12),
            (minimum_x + maximum_x) / 2.0,
            (minimum_y + maximum_y) / 2.0,
        )


class FreehandCanvas(QWidget):
    """Pointer adapter over FreehandCapture; conversion itself is dispatched by DesktopWindow."""

    completed = Signal(object)
    changed = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._capture = FreehandCapture()
        self.setMinimumSize(300, 220)
        self.setMouseTracking(True)
        self.setAccessibleName("Freehand source canvas")

    def reset(self) -> None:
        self._capture.reset()
        self.changed.emit(self._capture.snapshot())
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() is Qt.MouseButton.LeftButton:
            self._capture.pointer_down(self._point(event.position()))
            self.changed.emit(self._capture.snapshot())
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._capture.pointer_move(self._point(event.position()))
            self.changed.emit(self._capture.snapshot())
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() is Qt.MouseButton.LeftButton:
            snapshot = self._capture.pointer_up()
            self.changed.emit(snapshot)
            if snapshot.state is CaptureState.READY:
                self.completed.emit(snapshot)
            self.update()

    def paintEvent(self, _event: object) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#ffffff"))
        points = self._capture.snapshot().points
        if len(points) < 2:
            return
        path = QPainterPath(self._screen_point(points[0]))
        for point in points[1:]:
            path.lineTo(self._screen_point(point))
        painter.setPen(QPen(QColor("#1d4ed8"), 2.0))
        painter.drawPath(path)

    def _point(self, position: QPointF) -> Point2D:
        return Point2D(
            float(position.x() - self.width() / 2.0),
            float(self.height() / 2.0 - position.y()),
        )

    def _screen_point(self, point: Point2D) -> QPointF:
        return QPointF(point.x + self.width() / 2.0, self.height() / 2.0 - point.y)


class DesktopWindow(QMainWindow):
    """Desktop workflow with bounded worker shutdown and explicit UI states."""

    def __init__(self, *, locale: str | None = None) -> None:
        super().__init__()
        self._translator = Translator(resolve_locale(locale))
        self._image = ImageMvpController()
        self._timeline: EpicycleTimeline | None = None
        self._job: _Job | None = None
        self._job_generation = 0
        self._close_pending = False
        self._settings = QSettings("fourier-sketch", "desktop")
        self._last_tick = monotonic()
        self._canvas = EpicycleCanvas(self._translator)
        self._pages: QStackedWidget
        self._export_nav: QPushButton
        self._export_format: QComboBox
        self._export_frames: QSpinBox
        self._export_duration: QSpinBox
        self._export_action: QPushButton
        self._visibility_toggles: dict[str, QCheckBox] = {}
        self._inspector_list: QListWidget
        self._inspector_message: QLabel
        self._inspector_values: dict[str, QLabel] = {}
        self._inspector_frequencies: tuple[int, ...] = ()
        self._selected_harmonic_frequency: int | None = None
        self._current_frame: EpicycleFrame | None = None
        self._status = QLabel()
        self._source = FreehandCanvas()
        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._tick)
        self._build()
        self._restore_settings()

    def _build(self) -> None:
        self.setWindowTitle(self._translator.text("app.title"))
        root = QWidget()
        layout = QHBoxLayout(root)
        sidebar = QVBoxLayout()
        source_button = QPushButton(self._translator.text("desktop.page.source"))
        source_button.setAccessibleName("Source page")
        source_button.clicked.connect(lambda: self._pages.setCurrentIndex(0))
        sidebar.addWidget(source_button)
        for key in ("monochrome", "edges", "contours", "curve", "spectrum"):
            button = QPushButton(self._translator.text(f"desktop.page.{key}"))
            button.setEnabled(False)
            button.setToolTip(self._translator.text("desktop.deferred"))
            sidebar.addWidget(button)
        self._export_nav = QPushButton(self._translator.text("desktop.page.export"))
        self._export_nav.setEnabled(False)
        self._export_nav.setToolTip(self._translator.text("desktop.export.needs_timeline"))
        self._export_nav.clicked.connect(lambda: self._pages.setCurrentIndex(1))
        sidebar.addWidget(self._export_nav)
        sidebar.addStretch(1)
        layout.addLayout(sidebar)
        self._pages = QStackedWidget()
        source_page = QWidget()
        source_layout = QVBoxLayout(source_page)
        source_layout.setContentsMargins(9, 9, 9, _SOURCE_LAYOUT_BOTTOM_RESERVE)
        instructions = QLabel(self._translator.text("desktop.source.instructions"))
        instructions.setWordWrap(True)
        instructions.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Maximum,
        )
        source_layout.addWidget(instructions)
        self._source.setMaximumHeight(450)
        source_layout.addWidget(self._source)
        buttons = QHBoxLayout()
        clear = QPushButton(self._translator.text("desktop.source.clear"))
        clear.clicked.connect(self._source.reset)
        image = QPushButton(self._translator.text("desktop.source.choose_image"))
        image.clicked.connect(self._choose_image)
        self._dark_ink = QCheckBox(self._translator.text("desktop.source.dark_ink"))
        self._dark_ink.setChecked(True)
        self._dark_ink.setAccessibleName("Dark drawing on light background")
        buttons.addWidget(clear)
        buttons.addWidget(image)
        source_layout.addLayout(buttons)
        source_layout.addWidget(self._dark_ink)
        self._pages.addWidget(source_page)
        export_page = QWidget()
        export_layout = QVBoxLayout(export_page)
        export_instructions = QLabel(self._translator.text("desktop.export.instructions"))
        export_instructions.setWordWrap(True)
        export_layout.addWidget(export_instructions)
        export_form = QFormLayout()
        self._export_format = QComboBox()
        for export_format in ExportFormat:
            self._export_format.addItem(
                self._translator.text(f"desktop.export.format.{export_format.value}"),
                export_format.value,
            )
        self._export_frames = QSpinBox()
        self._export_frames.setRange(2, 120)
        self._export_frames.setValue(60)
        self._export_duration = QSpinBox()
        self._export_duration.setRange(20, 1000)
        self._export_duration.setValue(33)
        export_form.addRow(self._translator.text("desktop.export.format"), self._export_format)
        export_form.addRow(self._translator.text("desktop.export.frames"), self._export_frames)
        export_form.addRow(
            self._translator.text("desktop.export.frame_duration"), self._export_duration
        )
        export_layout.addLayout(export_form)
        self._export_action = QPushButton(self._translator.text("desktop.export.save"))
        self._export_action.setEnabled(False)
        self._export_action.clicked.connect(self._choose_export)
        self._export_format.currentIndexChanged.connect(self._export_format_changed)
        export_layout.addWidget(self._export_action)
        export_layout.addStretch(1)
        self._pages.addWidget(export_page)
        layout.addWidget(self._pages, 1)
        center = QVBoxLayout()
        center.addWidget(self._canvas, 1)
        center.addWidget(self._status)
        controls = QHBoxLayout()
        self._play = QPushButton(self._translator.text("control.play"))
        self._pause = QPushButton(self._translator.text("control.pause"))
        restart = QPushButton(self._translator.text("control.restart"))
        self._cancel = QPushButton(self._translator.text("desktop.control.cancel"))
        self._cancel.setEnabled(False)
        self._play.clicked.connect(lambda: self._timeline_action("play"))
        self._pause.clicked.connect(lambda: self._timeline_action("pause"))
        restart.clicked.connect(lambda: self._timeline_action("restart"))
        self._cancel.clicked.connect(self._cancel_current_job)
        controls.addWidget(self._play)
        controls.addWidget(self._pause)
        controls.addWidget(restart)
        controls.addWidget(self._cancel)
        center.addLayout(controls)
        options = QFormLayout()
        self._harmonics = QSlider(Qt.Orientation.Horizontal)
        self._speed = QSlider(Qt.Orientation.Horizontal)
        self._zoom = QSlider(Qt.Orientation.Horizontal)
        self._speed.setRange(
            int(_SPEED_MIN * _SPEED_SCALE),
            int(_SPEED_MAX * _SPEED_SCALE),
        )
        self._speed.setSingleStep(1)
        self._speed.setPageStep(5)
        self._speed.setValue(int(_SPEED_MIN * _SPEED_SCALE))
        self._zoom.setRange(
            int(_VIEW_ZOOM_MIN * _VIEW_ZOOM_SCALE),
            int(_VIEW_ZOOM_MAX * _VIEW_ZOOM_SCALE),
        )
        self._zoom.setSingleStep(1)
        self._zoom.setPageStep(100)
        self._zoom.setValue(int(_VIEW_ZOOM_DEFAULT * _VIEW_ZOOM_SCALE))
        self._harmonics.valueChanged.connect(
            lambda value: self._timeline_action("harmonics", value)
        )
        self._speed.valueChanged.connect(
            lambda value: self._timeline_action("speed", value / _SPEED_SCALE)
        )
        self._zoom.valueChanged.connect(
            lambda value: self._canvas.set_view_zoom(value / _VIEW_ZOOM_SCALE)
        )
        self._canvas.view_zoom_changed.connect(self._sync_zoom_control)
        options.addRow(self._translator.text("control.harmonics"), self._harmonics)
        options.addRow(self._translator.text("control.speed"), self._speed)
        reset_view = QPushButton(self._translator.text("control.reset_view"))
        reset_view.setAccessibleName("Reset canvas view")
        reset_view.clicked.connect(self._reset_canvas_view)
        options.addRow(self._translator.text("control.zoom"), self._zoom)
        options.addRow(reset_view)
        for field in ("circles", "vectors", "endpoint", "original", "reconstruction"):
            toggle = QCheckBox(self._translator.text(f"control.{field}"))
            toggle.setChecked(field != "original")
            toggle.setEnabled(False)
            toggle.toggled.connect(
                lambda checked, selected=field: self._set_visibility(selected, checked)
            )
            self._visibility_toggles[field] = toggle
            options.addRow(toggle)
        center.addLayout(options)
        layout.addLayout(center, 2)
        inspector = QGroupBox(self._translator.text("desktop.inspector.title"))
        inspector.setAccessibleName(self._translator.text("desktop.inspector.title"))
        inspector.setMinimumWidth(220)
        inspector.setMaximumWidth(320)
        inspector_layout = QVBoxLayout(inspector)
        self._inspector_message = QLabel(self._translator.text("desktop.inspector.empty"))
        self._inspector_message.setWordWrap(True)
        inspector_layout.addWidget(self._inspector_message)
        self._inspector_list = QListWidget()
        self._inspector_list.setAccessibleName(
            self._translator.text("desktop.inspector.list")
        )
        self._inspector_list.setEnabled(False)
        self._inspector_list.currentItemChanged.connect(self._inspector_row_changed)
        inspector_layout.addWidget(self._inspector_list, 1)
        inspector_form = QFormLayout()
        for key in (
            "position",
            "frequency",
            "amplitude",
            "phase",
            "angular_velocity",
            "local_value",
        ):
            value = QLabel("—")
            value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByKeyboard)
            value.setAccessibleName(self._translator.text(f"desktop.inspector.{key}"))
            self._inspector_values[key] = value
            inspector_form.addRow(
                self._translator.text(f"desktop.inspector.{key}"),
                value,
            )
        inspector_layout.addLayout(inspector_form)
        layout.addWidget(inspector)
        self.setCentralWidget(root)
        self._source.completed.connect(self._build_freehand)
        self._source.changed.connect(self._capture_changed)
        self._canvas.harmonic_selected.connect(self._canvas_harmonic_selected)
        self._set_status(self._translator.text("desktop.status.initial"))

    def _capture_changed(self, snapshot: object) -> None:
        count = len(getattr(snapshot, "points", ()))
        self._set_status(self._translator.text("desktop.status.captured", count=count))

    def _build_freehand(self, snapshot: object) -> None:
        points = tuple(getattr(snapshot, "points", ()))
        if not points:
            return
        reference_view_size = (float(self._source.width()), float(self._source.height()))

        def operation() -> EpicycleTimeline:
            curve = Curve(points, closed=False)
            return build_freehand_timeline(curve)

        self._start_job(
            operation,
            lambda result: self._apply_timeline(
                result,
                reference_view_size=reference_view_size,
            ),
        )

    def _choose_image(self) -> None:
        name, _ = QFileDialog.getOpenFileName(
            self,
            self._translator.text("desktop.source.dialog"),
            filter=self._translator.text("desktop.source.filter"),
        )
        if not name:
            return
        generation = self._image.begin(
            ImageMvpConfig(
                preprocessing=ImagePreprocessingOptions(invert=self._dark_ink.isChecked())
            )
        )
        self._set_status(self._translator.text("desktop.status.processing"))
        self._start_job(lambda: self._image.process(generation, Path(name)), self._apply_image)

    def _start_job(
        self,
        operation: Callable[[], object],
        on_success: Callable[[object], None],
        *,
        on_progress: Callable[[int], None] | None = None,
    ) -> None:
        if self._job is not None and self._job.isRunning():
            self._set_status(self._translator.text("desktop.status.busy"))
            return
        self._job_generation += 1
        generation = self._job_generation
        self._job = _Job(operation)
        self._cancel.setEnabled(True)

        def on_job_success(result: object, expected: int = generation) -> None:
            if self._job_generation != expected:
                return
            on_success(result)

        def on_job_failed(_key: str, expected: int = generation) -> None:
            if self._job_generation != expected:
                return
            self._set_status(self._translator.text("desktop.status.runtime"))

        self._job.finished_snapshot.connect(on_job_success)
        self._job.failed.connect(on_job_failed)
        if on_progress is not None:
            self._job.progress.connect(on_progress)
        self._job.finished.connect(self._job_finished)
        self._job.start()

    def _cancel_current_job(self) -> None:
        self._image.cancel()
        self._job_generation += 1
        job = self._job
        if job is None:
            return

        if job.isRunning():
            job.requestInterruption()
            self._cancel.setEnabled(False)
        if not job.isRunning():
            self._job = None
            job.deleteLater()
            self._cancel.setEnabled(False)
        self._set_status(self._translator.text("desktop.status.cancelled"))

    def _set_visibility(self, field: str, enabled: bool) -> None:
        timeline = self._timeline
        if timeline is None:
            return
        try:
            self._apply_frame(timeline.set_visibility(**{field: enabled}))
        except DomainValidationError:
            self._set_status(self._translator.text("desktop.status.invalid_control"))

    def _job_finished(self) -> None:
        if self._job is not None:
            self._job.deleteLater()
        self._job = None
        self._cancel.setEnabled(False)
        if self._close_pending:
            self._close_pending = False
            QTimer.singleShot(0, self.close)

    def _apply_image(self, snapshot: object) -> None:
        if not isinstance(snapshot, ImageMvpSnapshot):
            self._set_status(self._translator.text("desktop.status.runtime"))
            return
        if snapshot.state is ImageMvpState.READY:
            result = snapshot.result
            if result is not None and hasattr(result, "timeline"):
                self._apply_timeline(result.timeline)
            else:
                self._set_status(self._translator.text("desktop.status.runtime"))
            return
        if snapshot.state is ImageMvpState.EMPTY:
            self._set_status(self._translator.text("desktop.status.empty"))
        elif snapshot.state is ImageMvpState.CANCELLED:
            self._set_status(self._translator.text("desktop.status.cancelled"))
        else:
            self._set_status(
                self._translator.text(snapshot.failure_key or "image_mvp.error.runtime")
            )

    def _apply_timeline(
        self,
        timeline: object,
        *,
        reference_view_size: tuple[float, float] | None = None,
    ) -> None:
        if not isinstance(timeline, EpicycleTimeline):
            self._set_status(self._translator.text("desktop.status.runtime"))
            return
        self._reset_harmonic_inspector()
        self._timeline = timeline
        self._canvas.set_reference_view_size(reference_view_size)
        self._canvas.reset_view()
        for toggle in self._visibility_toggles.values():
            blocked = toggle.blockSignals(True)
            toggle.setChecked(True)
            toggle.setEnabled(True)
            toggle.blockSignals(blocked)
        self._export_nav.setEnabled(True)
        self._export_format_changed()
        speed = self._speed.value() / _SPEED_SCALE
        self._apply_frame(timeline.set_speed(speed))

    def _export_format_changed(self) -> None:
        export_format = self._selected_export_format()
        is_mp4 = export_format is ExportFormat.MP4
        self._export_action.setEnabled(self._timeline is not None and not is_mp4)
        self._export_frames.setEnabled(export_format is ExportFormat.GIF)
        self._export_duration.setEnabled(export_format is ExportFormat.GIF)
        if is_mp4:
            self._export_action.setToolTip(mp4_capability().reason)
            self._set_status(self._translator.text("desktop.export.mp4_unavailable"))
        else:
            self._export_action.setToolTip("")

    def _choose_export(self) -> None:
        timeline = self._timeline
        export_format = self._selected_export_format()
        if timeline is None:
            return
        if export_format is ExportFormat.MP4:
            self._set_status(self._translator.text("desktop.export.mp4_unavailable"))
            return
        suffix, filter_key = _export_dialog_contract(export_format)
        name, _ = QFileDialog.getSaveFileName(
            self,
            self._translator.text("desktop.export.dialog"),
            filter=self._translator.text(filter_key),
        )
        if not name:
            return
        output = Path(name)
        if output.suffix.lower() != suffix:
            output = output.with_suffix(suffix)
        try:
            validate_local_path(output, field_name="export output")
        except DomainValidationError:
            self._set_status(self._translator.text("desktop.status.invalid_control"))
            return
        overwrite = False
        if output.exists():
            answer = QMessageBox.question(
                self,
                self._translator.text("desktop.export.overwrite_title"),
                self._translator.text(
                    "desktop.export.overwrite_message", name=safe_display_basename(output)
                ),
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            overwrite = True
        frame = timeline.snapshot()
        frame_count = self._export_frames.value()
        frame_duration_ms = self._export_duration.value()

        def operation() -> Path:
            def cancelled() -> bool:
                return QThread.currentThread().isInterruptionRequested()

            if export_format in {ExportFormat.CURVE_JSON, ExportFormat.CURVE_CSV}:
                return export_curve_data(
                    frame.original,
                    output,
                    format=export_format,
                    overwrite=overwrite,
                    cancelled=cancelled,
                )
            if export_format in {
                ExportFormat.COEFFICIENTS_JSON,
                ExportFormat.COEFFICIENTS_CSV,
            }:
                return export_coefficient_data(
                    frame.selection,
                    output,
                    format=export_format,
                    overwrite=overwrite,
                    cancelled=cancelled,
                )
            if export_format is ExportFormat.RECONSTRUCTION_PNG:
                return render_frame_png(
                    frame,
                    output,
                    self._translator,
                    overwrite=overwrite,
                    cancelled=cancelled,
                )
            if export_format is ExportFormat.SPECTRUM_PNG:
                return render_spectrum_png(
                    frame.selection,
                    output,
                    self._translator,
                    overwrite=overwrite,
                    cancelled=cancelled,
                )
            if export_format is ExportFormat.GIF:
                plan = AnimationExportPlan(
                    frame,
                    frame_count=frame_count,
                    frame_duration_ms=frame_duration_ms,
                )

                def progress(value: int) -> None:
                    current = QThread.currentThread()
                    if isinstance(current, _Job):
                        current.progress.emit(value)

                return export_animation_gif(
                    plan,
                    output,
                    self._translator,
                    overwrite=overwrite,
                    cancelled=cancelled,
                    progress=progress,
                )
            raise DomainValidationError("unsupported export format")

        self._set_status(self._translator.text("desktop.export.processing"))
        self._start_job(
            operation,
            self._apply_export_result,
            on_progress=lambda value: self._set_status(
                self._translator.text("desktop.export.progress", progress=value)
            ),
        )

    def _apply_export_result(self, result: object) -> None:
        if not isinstance(result, Path):
            self._set_status(self._translator.text("desktop.status.runtime"))
            return
        self._set_status(
            self._translator.text("desktop.export.completed", name=safe_display_basename(result))
        )

    def _selected_export_format(self) -> ExportFormat:
        try:
            return ExportFormat(str(self._export_format.currentData()))
        except ValueError as error:
            raise DomainValidationError("desktop export format selection is invalid") from error

    def _apply_frame(self, frame: object) -> None:
        if not isinstance(frame, EpicycleFrame):
            self._set_status(self._translator.text("desktop.status.runtime"))
            return
        self._current_frame = frame
        self._canvas.set_frame(frame)
        self._sync_harmonic_inspector(frame)
        for field, toggle in self._visibility_toggles.items():
            blocked = toggle.blockSignals(True)
            toggle.setChecked(bool(getattr(frame.visibility, field)))
            toggle.setEnabled(True)
            toggle.blockSignals(blocked)
        harmonics_blocked = self._harmonics.blockSignals(True)
        self._harmonics.setRange(1, frame.selection.sample_count)
        self._harmonics.setValue(frame.selection.coefficient_count)
        self._harmonics.blockSignals(harmonics_blocked)
        self._set_status(
            self._translator.text(
                "status.summary",
                state=frame.timeline_state,
                time=frame.chain.time,
                harmonics=frame.selection.coefficient_count,
                speed=frame.speed,
            )
        )

    def _reset_harmonic_inspector(self) -> None:
        self._selected_harmonic_frequency = None
        self._current_frame = None
        self._inspector_frequencies = ()
        blocked = self._inspector_list.blockSignals(True)
        self._inspector_list.clear()
        self._inspector_list.blockSignals(blocked)
        self._inspector_list.setEnabled(False)
        self._canvas.set_selected_harmonic(None)
        self._set_inspector_item(None, message_key="desktop.inspector.empty")

    def _sync_harmonic_inspector(self, frame: EpicycleFrame) -> None:
        frequencies = frame.selection.frequencies
        if frequencies != self._inspector_frequencies:
            blocked = self._inspector_list.blockSignals(True)
            self._inspector_list.clear()
            for index, frequency in enumerate(frequencies):
                row = QListWidgetItem(
                    self._translator.text(
                        "desktop.inspector.row",
                        position=index + 1,
                        frequency=frequency,
                    )
                )
                row.setData(Qt.ItemDataRole.UserRole, frequency)
                self._inspector_list.addItem(row)
            self._inspector_list.blockSignals(blocked)
            self._inspector_frequencies = frequencies
        self._inspector_list.setEnabled(True)

        stale_selection = (
            self._selected_harmonic_frequency is not None
            and self._selected_harmonic_frequency not in frequencies
        )
        if stale_selection:
            self._selected_harmonic_frequency = None
        selected = self._selected_harmonic_frequency
        if selected is None:
            blocked = self._inspector_list.blockSignals(True)
            self._inspector_list.setCurrentRow(-1)
            self._inspector_list.blockSignals(blocked)
            self._canvas.set_selected_harmonic(None)
            self._set_inspector_item(
                None,
                message_key=(
                    "desktop.inspector.stale"
                    if stale_selection
                    else "desktop.inspector.select"
                ),
            )
            return

        item = build_harmonic_inspector_item(frame.selection, frame.chain, selected)
        if item is None:
            self._selected_harmonic_frequency = None
            self._canvas.set_selected_harmonic(None)
            self._set_inspector_item(None, message_key="desktop.inspector.stale")
            return
        blocked = self._inspector_list.blockSignals(True)
        self._inspector_list.setCurrentRow(item.selection_index)
        self._inspector_list.blockSignals(blocked)
        self._canvas.set_selected_harmonic(item.frequency)
        self._set_inspector_item(item)

    def _set_inspector_item(
        self,
        item: HarmonicInspectorItem | None,
        *,
        message_key: str = "desktop.inspector.selected",
    ) -> None:
        self._inspector_message.setText(self._translator.text(message_key))
        if item is None:
            for value in self._inspector_values.values():
                value.setText("—")
            return
        self._inspector_values["position"].setText(
            f"{item.selection_index + 1}/{len(self._inspector_frequencies)}"
        )
        self._inspector_values["frequency"].setText(str(item.frequency))
        self._inspector_values["amplitude"].setText(f"{item.amplitude:.6g}")
        self._inspector_values["phase"].setText(f"{item.phase:.6g}")
        self._inspector_values["angular_velocity"].setText(
            f"{item.angular_velocity:.6g}"
        )
        self._inspector_values["local_value"].setText(
            f"{item.local_value.real:+.6g} {item.local_value.imag:+.6g}i"
        )

    def _select_harmonic(self, frequency: int | None) -> None:
        self._selected_harmonic_frequency = frequency
        frame = self._current_frame
        if frame is None:
            self._reset_harmonic_inspector()
            return
        self._sync_harmonic_inspector(frame)

    def _canvas_harmonic_selected(self, value: object) -> None:
        frequency = value if type(value) is int else None
        self._select_harmonic(frequency)

    def _inspector_row_changed(
        self,
        current: QListWidgetItem | None,
        _previous: QListWidgetItem | None,
    ) -> None:
        if current is None:
            self._select_harmonic(None)
            return
        value = current.data(Qt.ItemDataRole.UserRole)
        self._select_harmonic(value if type(value) is int else None)

    def _timeline_action(self, action: str, value: float | int | None = None) -> None:
        timeline = self._timeline
        if timeline is None:
            return
        try:
            result = {
                "play": timeline.play,
                "pause": timeline.pause,
                "restart": timeline.restart,
            }.get(action)
            if result is not None:
                next_frame = result()
                if action == "play":
                    self._last_tick = monotonic()
                    self._timer.start()
                else:
                    self._timer.stop()
            elif action == "harmonics":
                if value is None:
                    return
                next_frame = timeline.set_harmonic_count(int(value))
            elif action == "speed":
                if value is None:
                    return
                next_frame = timeline.set_speed(float(value))
            elif action == "advance":
                if value is None:
                    return
                next_frame = timeline.advance(float(value))
            else:
                return
            self._apply_frame(next_frame)
        except DomainValidationError:
            self._set_status(self._translator.text("desktop.status.invalid_control"))

    def _tick(self) -> None:
        timeline = self._timeline
        if timeline is None or timeline.state is TimelineState.PAUSED:
            self._timer.stop()
            return
        now = monotonic()
        delta = now - self._last_tick
        self._last_tick = now
        self._timeline_action("advance", delta)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self._cancel_current_job()
            event.accept()
            return
        if event.key() == Qt.Key.Key_R:
            self._source.reset()
            self._timeline_action("restart")
            event.accept()
            return
        if event.key() == Qt.Key.Key_Space:
            timeline = self._timeline
            if timeline is not None:
                action = "pause" if timeline.state.value == "running" else "play"
                self._timeline_action(action)
            event.accept()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event: QCloseEvent) -> None:
        self._save_settings()
        self._timer.stop()
        self._cancel_current_job()
        if self._job is not None and self._job.isRunning():
            self._close_pending = True
            event.ignore()
            return
        event.accept()

    def _set_status(self, text: str) -> None:
        self._status.setText(text)

    def _reset_canvas_view(self) -> None:
        self._canvas.reset_view()

    def _sync_zoom_control(self, zoom: float) -> None:
        self._zoom.setValue(round(zoom * _VIEW_ZOOM_SCALE))

    def _restore_settings(self) -> None:
        window_width = cast(int, self._settings.value("window/width", 1200, int))
        window_height = cast(int, self._settings.value("window/height", 760, int))
        speed_settings_version = cast(
            int,
            self._settings.value("controls/speed_schema", 1, int),
        )
        control_speed = (
            cast(
                int,
                self._settings.value("controls/speed", self._speed.minimum(), int),
            )
            if speed_settings_version == _SPEED_SETTINGS_VERSION
            else self._speed.minimum()
        )
        control_harmonics = cast(int, self._settings.value("controls/harmonics", 1, int))
        view_zoom = cast(
            int,
            self._settings.value(
                "controls/view_zoom", int(_VIEW_ZOOM_DEFAULT * _VIEW_ZOOM_SCALE), int
            ),
        )
        self.resize(
            window_width,
            window_height,
        )
        self._speed.setValue(
            max(
                self._speed.minimum(),
                min(
                    self._speed.maximum(),
                    control_speed,
                ),
            )
        )
        self._harmonics.setValue(
            max(
                self._harmonics.minimum(),
                min(
                    self._harmonics.maximum(),
                    control_harmonics,
                ),
            )
        )
        self._zoom.setValue(
            max(
                self._zoom.minimum(),
                min(
                    self._zoom.maximum(),
                    view_zoom,
                ),
            )
        )

    def _save_settings(self) -> None:
        self._settings.setValue("window/width", self.width())
        self._settings.setValue("window/height", self.height())
        self._settings.setValue("controls/speed_schema", _SPEED_SETTINGS_VERSION)
        self._settings.setValue("controls/speed", self._speed.value())
        self._settings.setValue("controls/harmonics", self._harmonics.value())
        self._settings.setValue("controls/view_zoom", self._zoom.value())


def run_desktop(*, locale: str | None = None) -> int:
    app = QApplication.instance() or QApplication([])
    window = DesktopWindow(locale=locale)
    window.show()
    return app.exec()
