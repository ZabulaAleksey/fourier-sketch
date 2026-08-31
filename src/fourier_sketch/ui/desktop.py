"""Responsive PySide6 shell that only dispatches existing application use cases."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from math import degrees, hypot, isfinite, radians
from pathlib import Path
from time import monotonic
from typing import cast

from PySide6.QtCore import QEvent, QLineF, QPointF, QSettings, Qt, QThread, QTimer, Signal
from PySide6.QtGui import (
    QCloseEvent,
    QColor,
    QEventPoint,
    QKeyEvent,
    QKeySequence,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
    QShortcut,
    QTouchEvent,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
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
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from fourier_sketch.application import (
    CANONICAL_CIRCLE_FREQUENCY,
    AnimationExportPlan,
    BuildUpSnapshot,
    BuildUpState,
    CanonicalCircleLesson,
    CaptureState,
    EducationalModeSession,
    EducationalSnapshot,
    EducationalUnavailable,
    EpicycleFrame,
    EpicycleTimeline,
    ExportFormat,
    FreehandCapture,
    FrequencySoloSession,
    HaarFrame,
    HaarTimeline,
    HarmonicBuildUpSession,
    HarmonicPlaygroundSession,
    ImageMvpConfig,
    ImageMvpController,
    ImageMvpSnapshot,
    ImageMvpState,
    IndexedBasisFrame,
    IndexedBasisTimeline,
    TimelineState,
    build_basis_timeline,
    build_canonical_circle_lesson,
    export_coefficient_data,
    export_curve_data,
    mp4_capability,
    safe_display_basename,
    validate_local_path,
)
from fourier_sketch.domain import (
    BasisKind,
    Curve,
    DomainValidationError,
    ManualHarmonic,
    Point2D,
    SpectrumOrdering,
)
from fourier_sketch.imaging import ImagePreprocessingOptions
from fourier_sketch.presentation import Translator, format_educational_copy, resolve_locale
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
        self._haar_frame: HaarFrame | None = None
        self._indexed_frame: IndexedBasisFrame | None = None
        self._frame_cache_key: tuple[int, int, tuple[int, ...]] | None = None
        self._scene_bounds: tuple[float, float, float, float] | None = None
        self._reference_view_size: tuple[float, float] | None = None
        self._original_scene_path = QPainterPath()
        self._reconstruction_scene_path = QPainterPath()
        self._haar_contribution_scene_path = QPainterPath()
        self._haar_visibility = {"original": True, "reconstruction": True}
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
        self._educational_sample: Point2D | None = None
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
    def reference_view_size(self) -> tuple[float, float] | None:
        return self._reference_view_size

    def restore_view_state(
        self,
        zoom: float,
        pan: tuple[float, float],
        reference_view_size: tuple[float, float] | None,
    ) -> None:
        """Restore a previously captured presentation-only viewport exactly."""

        next_zoom = _bounded_view_zoom(zoom)
        pan_x, pan_y = pan
        if not isfinite(pan_x) or not isfinite(pan_y):
            raise DomainValidationError("view pan must contain finite values")
        self.set_reference_view_size(reference_view_size)
        self._view_zoom = next_zoom
        self._view_pan = QPointF(float(pan_x), float(pan_y))
        self.update()
        self.view_zoom_changed.emit(self._view_zoom)

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

    @property
    def educational_sample(self) -> Point2D | None:
        """Return the presentation-only lesson sample marker."""

        return self._educational_sample

    def set_educational_sample(self, sample: Point2D | None) -> None:
        """Highlight one actual source sample without changing the frame."""

        selected = sample
        frame = self._frame
        if selected is not None and (
            not isinstance(selected, Point2D)
            or frame is None
            or selected not in frame.original.points
        ):
            selected = None
        if selected == self._educational_sample:
            return
        self._educational_sample = selected
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
        self._haar_frame = None
        self._indexed_frame = None
        self.setAccessibleName("Epicycles canvas")
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
            self._educational_sample = None
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
            if self._educational_sample not in frame.original.points:
                self._educational_sample = None
        self._frame = frame
        self.update()

    def set_haar_frame(self, frame: HaarFrame | None) -> None:
        """Display one actual Haar reconstruction without fabricating epicycle state."""

        self._frame = None
        self._indexed_frame = None
        self._selected_harmonic_frequency = None
        self._educational_sample = None
        self._vector_lines = []
        self._circle_centers = []
        self._vector_colors = []
        self._circle_colors = []
        self._frame_cache_key = None
        if frame is None:
            self._haar_frame = None
            self._scene_bounds = None
            self._original_scene_path = QPainterPath()
            self._reconstruction_scene_path = QPainterPath()
            self._haar_contribution_scene_path = QPainterPath()
            self.setAccessibleName("Epicycles canvas")
            self.update()
            return
        source_points = frame.source.points + (
            (frame.source.start,) if frame.source.closed else ()
        )
        reconstruction_points = frame.reconstruction.points + (
            (frame.reconstruction.start,) if frame.reconstruction.closed else ()
        )
        contribution_points = frame.active_contribution.points + (
            (frame.active_contribution.start,) if frame.active_contribution.closed else ()
        )
        self._original_scene_path, source_bounds = self._build_scene_path(source_points)
        self._reconstruction_scene_path, reconstruction_bounds = self._build_scene_path(
            reconstruction_points
        )
        self._haar_contribution_scene_path, contribution_bounds = self._build_scene_path(
            contribution_points
        )
        self._scene_bounds = (
            min(source_bounds[0], reconstruction_bounds[0], contribution_bounds[0]),
            max(source_bounds[1], reconstruction_bounds[1], contribution_bounds[1]),
            min(source_bounds[2], reconstruction_bounds[2], contribution_bounds[2]),
            max(source_bounds[3], reconstruction_bounds[3], contribution_bounds[3]),
        )
        self._haar_frame = frame
        self.setAccessibleName(self._translator.text("basis.haar.accessible"))
        self.update()

    def set_indexed_basis_frame(self, frame: IndexedBasisFrame | None) -> None:
        """Display an indexed-basis reconstruction without epicycle semantics."""

        self._frame = None
        self._haar_frame = None
        self._selected_harmonic_frequency = None
        self._educational_sample = None
        self._vector_lines = []
        self._circle_centers = []
        self._vector_colors = []
        self._circle_colors = []
        self._frame_cache_key = None
        if frame is None:
            self._indexed_frame = None
            self._scene_bounds = None
            self._original_scene_path = QPainterPath()
            self._reconstruction_scene_path = QPainterPath()
            self._haar_contribution_scene_path = QPainterPath()
            self.setAccessibleName("Epicycles canvas")
            self.update()
            return
        source_points = frame.source.points + (
            (frame.source.start,) if frame.source.closed else ()
        )
        reconstruction_points = frame.reconstruction.points + (
            (frame.reconstruction.start,) if frame.reconstruction.closed else ()
        )
        contribution_points = frame.active_contribution.points + (
            (frame.active_contribution.start,) if frame.active_contribution.closed else ()
        )
        self._original_scene_path, source_bounds = self._build_scene_path(source_points)
        self._reconstruction_scene_path, reconstruction_bounds = self._build_scene_path(
            reconstruction_points
        )
        self._haar_contribution_scene_path, contribution_bounds = self._build_scene_path(
            contribution_points
        )
        self._scene_bounds = (
            min(source_bounds[0], reconstruction_bounds[0], contribution_bounds[0]),
            max(source_bounds[1], reconstruction_bounds[1], contribution_bounds[1]),
            min(source_bounds[2], reconstruction_bounds[2], contribution_bounds[2]),
            max(source_bounds[3], reconstruction_bounds[3], contribution_bounds[3]),
        )
        self._indexed_frame = frame
        self.setAccessibleName(
            self._translator.text(f"basis.{frame.basis.value}.accessible")
        )
        self.update()

    def set_haar_visibility(self, field: str, enabled: bool) -> None:
        """Set source/reconstruction visibility as presentation-only Haar state."""

        if field not in self._haar_visibility or not isinstance(enabled, bool):
            raise DomainValidationError("unsupported Haar visibility field")
        self._haar_visibility[field] = enabled
        self.update()

    def _build_scene_path(
        self, points: tuple[Point2D, ...]
    ) -> tuple[QPainterPath, tuple[float, float, float, float]]:
        if not points:
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
        haar_frame = self._haar_frame
        indexed_frame = self._indexed_frame
        if frame is None and haar_frame is None and indexed_frame is None:
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

        if haar_frame is not None or indexed_frame is not None:
            if self._haar_visibility["original"]:
                draw_path(self._original_scene_path, "#94a3b8", 1.0)
            if self._haar_visibility["reconstruction"]:
                draw_path(self._reconstruction_scene_path, "#14b8a6", 1.8)
            draw_path(self._haar_contribution_scene_path, "#7c3aed", 1.2)
            painter.restore()
            return
        if frame is None:
            painter.restore()
            return
        visibility = frame.visibility
        if visibility.original:
            draw_path(self._original_scene_path, "#94a3b8", 1.0)
        if visibility.reconstruction:
            draw_path(self._reconstruction_scene_path, "#14b8a6", 1.4)
        if self._educational_sample is not None:
            painter.setBrush(QColor("#7c3aed"))
            painter.setPen(QPen(QColor("#ffffff"), 1.2 * line_scale))
            painter.drawEllipse(
                map_point(self._educational_sample),
                5.0 * line_scale,
                5.0 * line_scale,
            )
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
        self._haar_timeline: HaarTimeline | None = None
        self._indexed_timeline: IndexedBasisTimeline | None = None
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
        self._solo = FrequencySoloSession()
        self._solo_mode: QLabel
        self._solo_action: QPushButton
        self._build_up = HarmonicBuildUpSession()
        self._build_up_snapshot: BuildUpSnapshot | None = None
        self._build_up_restore_frequency: int | None = None
        self._build_up_mode: QLabel
        self._build_up_action: QPushButton
        self._build_up_ordering: QComboBox
        self._build_up_target: QSpinBox
        self._build_up_dwell: QSpinBox
        self._educational = EducationalModeSession()
        self._educational_lesson: CanonicalCircleLesson | None = None
        self._educational_snapshot: EducationalSnapshot | None = None
        self._educational_mode: QLabel
        self._educational_body: QLabel
        self._educational_equation: QLabel
        self._educational_load: QPushButton
        self._educational_action: QPushButton
        self._educational_previous: QPushButton
        self._educational_next: QPushButton
        self._educational_restart: QPushButton
        self._educational_shortcuts: list[QShortcut] = []
        self._playground = HarmonicPlaygroundSession()
        self._playground_active = False
        self._playground_baseline: object | None = None
        self._playground_baseline_basis: BasisKind | None = None
        self._playground_baseline_visibility: dict[str, bool] | None = None
        self._playground_baseline_view: tuple[
            float,
            tuple[float, float],
            tuple[float, float] | None,
        ] | None = None
        self._playground_list: QListWidget
        self._playground_frequency: QSpinBox
        self._playground_amplitude: QDoubleSpinBox
        self._playground_phase: QDoubleSpinBox
        self._playground_toggle: QPushButton
        self._playground_apply: QPushButton
        self._playground_remove: QPushButton
        self._playground_clear: QPushButton
        self._playground_reset: QPushButton
        self._playground_mode: QLabel
        self._baseline_frame: EpicycleFrame | None = None
        self._current_frame: EpicycleFrame | None = None
        self._status = QLabel()
        self._source = FreehandCanvas()
        self._basis_selector: QComboBox
        self._term_label: QLabel
        self._image_button: QPushButton
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
        playground_button = QPushButton(
            self._translator.text("desktop.page.harmonic_playground")
        )
        playground_button.setAccessibleName(
            self._translator.text("desktop.page.harmonic_playground")
        )
        playground_button.clicked.connect(lambda: self._pages.setCurrentIndex(2))
        sidebar.addWidget(playground_button)
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
        self._basis_selector = QComboBox()
        for basis in BasisKind:
            self._basis_selector.addItem(
                self._translator.text(f"basis.{basis.value}"),
                basis.value,
            )
        self._basis_selector.currentIndexChanged.connect(self._basis_changed)
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
        buttons.addWidget(QLabel(self._translator.text("control.basis")))
        buttons.addWidget(self._basis_selector)
        clear = QPushButton(self._translator.text("desktop.source.clear"))
        clear.clicked.connect(self._reset_source)
        self._image_button = QPushButton(
            self._translator.text("desktop.source.choose_image")
        )
        self._image_button.clicked.connect(self._choose_image)
        self._dark_ink = QCheckBox(self._translator.text("desktop.source.dark_ink"))
        self._dark_ink.setChecked(True)
        self._dark_ink.setAccessibleName("Dark drawing on light background")
        buttons.addWidget(clear)
        buttons.addWidget(self._image_button)
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
        playground_page = QWidget()
        playground_layout = QVBoxLayout(playground_page)
        playground_intro = QLabel(
            self._translator.text("desktop.playground.instructions")
        )
        playground_intro.setWordWrap(True)
        playground_layout.addWidget(playground_intro)
        self._playground_mode = QLabel(
            self._translator.text("desktop.playground.inactive")
        )
        self._playground_mode.setWordWrap(True)
        playground_layout.addWidget(self._playground_mode)
        self._playground_toggle = QPushButton(
            self._translator.text("desktop.playground.enter")
        )
        self._playground_toggle.clicked.connect(self._toggle_playground)
        playground_layout.addWidget(self._playground_toggle)
        self._playground_list = QListWidget()
        self._playground_list.setAccessibleName(
            self._translator.text("desktop.playground.list")
        )
        self._playground_list.currentRowChanged.connect(
            self._playground_row_changed
        )
        playground_layout.addWidget(self._playground_list, 1)
        playground_form = QFormLayout()
        self._playground_frequency = QSpinBox()
        self._playground_frequency.setRange(-64, 63)
        self._playground_amplitude = QDoubleSpinBox()
        self._playground_amplitude.setRange(0.01, 4.0)
        self._playground_amplitude.setDecimals(2)
        self._playground_amplitude.setSingleStep(0.05)
        self._playground_amplitude.setValue(1.0)
        self._playground_phase = QDoubleSpinBox()
        self._playground_phase.setRange(-180.0, 180.0)
        self._playground_phase.setDecimals(1)
        self._playground_phase.setSingleStep(5.0)
        playground_form.addRow(
            self._translator.text("desktop.playground.frequency"),
            self._playground_frequency,
        )
        playground_form.addRow(
            self._translator.text("desktop.playground.amplitude"),
            self._playground_amplitude,
        )
        playground_form.addRow(
            self._translator.text("desktop.playground.phase"),
            self._playground_phase,
        )
        playground_layout.addLayout(playground_form)
        playground_actions = QHBoxLayout()
        self._playground_apply = QPushButton(
            self._translator.text("desktop.playground.apply")
        )
        self._playground_remove = QPushButton(
            self._translator.text("desktop.playground.remove")
        )
        self._playground_apply.clicked.connect(self._apply_playground_component)
        self._playground_remove.clicked.connect(self._remove_playground_component)
        playground_actions.addWidget(self._playground_apply)
        playground_actions.addWidget(self._playground_remove)
        playground_layout.addLayout(playground_actions)
        playground_reset_actions = QHBoxLayout()
        self._playground_clear = QPushButton(
            self._translator.text("desktop.playground.clear")
        )
        self._playground_reset = QPushButton(
            self._translator.text("desktop.playground.reset_circle")
        )
        self._playground_clear.clicked.connect(self._clear_playground)
        self._playground_reset.clicked.connect(self._reset_playground_circle)
        playground_reset_actions.addWidget(self._playground_clear)
        playground_reset_actions.addWidget(self._playground_reset)
        playground_layout.addLayout(playground_reset_actions)
        self._pages.addWidget(playground_page)
        self._refresh_playground_controls()
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
        self._term_label = QLabel(self._translator.text("control.harmonics"))
        options.addRow(self._term_label, self._harmonics)
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
        self._solo_mode = QLabel(self._translator.text("desktop.solo.inactive"))
        self._solo_mode.setWordWrap(True)
        self._solo_mode.setAccessibleName(self._translator.text("desktop.solo.mode"))
        inspector_layout.addWidget(self._solo_mode)
        self._solo_action = QPushButton(self._translator.text("desktop.solo.enter"))
        self._solo_action.setAccessibleName(self._translator.text("desktop.solo.enter"))
        self._solo_action.setEnabled(False)
        self._solo_action.clicked.connect(self._toggle_solo)
        inspector_layout.addWidget(self._solo_action)
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
        build_up = QGroupBox(self._translator.text("desktop.build_up.title"))
        build_up.setAccessibleName(self._translator.text("desktop.build_up.title"))
        build_up_layout = QVBoxLayout(build_up)
        self._build_up_mode = QLabel(self._translator.text("desktop.build_up.inactive"))
        self._build_up_mode.setWordWrap(True)
        self._build_up_mode.setAccessibleName(
            self._translator.text("desktop.build_up.mode")
        )
        build_up_layout.addWidget(self._build_up_mode)
        build_up_form = QFormLayout()
        self._build_up_ordering = QComboBox()
        for ordering in SpectrumOrdering:
            if ordering is SpectrumOrdering.EXPLICIT:
                continue
            self._build_up_ordering.addItem(
                self._translator.text(f"desktop.build_up.ordering.{ordering.value}"),
                ordering.value,
            )
        self._build_up_target = QSpinBox()
        self._build_up_target.setRange(1, 1)
        self._build_up_dwell = QSpinBox()
        self._build_up_dwell.setRange(100, 5000)
        self._build_up_dwell.setSingleStep(100)
        self._build_up_dwell.setValue(500)
        build_up_form.addRow(
            self._translator.text("desktop.build_up.ordering"),
            self._build_up_ordering,
        )
        build_up_form.addRow(
            self._translator.text("desktop.build_up.target"),
            self._build_up_target,
        )
        build_up_form.addRow(
            self._translator.text("desktop.build_up.dwell"),
            self._build_up_dwell,
        )
        build_up_layout.addLayout(build_up_form)
        self._build_up_action = QPushButton(
            self._translator.text("desktop.build_up.start")
        )
        self._build_up_action.setAccessibleName(
            self._translator.text("desktop.build_up.start")
        )
        self._build_up_action.setEnabled(False)
        self._build_up_action.clicked.connect(self._toggle_build_up)
        build_up_layout.addWidget(self._build_up_action)
        inspector_layout.addWidget(build_up)
        educational = QGroupBox(self._translator.text("desktop.educational.title"))
        educational.setAccessibleName(self._translator.text("desktop.educational.title"))
        educational_layout = QVBoxLayout(educational)
        self._educational_mode = QLabel(
            self._translator.text("desktop.educational.unavailable")
        )
        self._educational_mode.setWordWrap(True)
        self._educational_mode.setAccessibleName(
            self._translator.text("desktop.educational.mode")
        )
        educational_layout.addWidget(self._educational_mode)
        self._educational_body = QLabel("")
        self._educational_body.setWordWrap(True)
        educational_layout.addWidget(self._educational_body)
        self._educational_equation = QLabel("")
        self._educational_equation.setWordWrap(True)
        self._educational_equation.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        educational_layout.addWidget(self._educational_equation)
        self._educational_load = QPushButton(
            self._translator.text("desktop.educational.load")
        )
        self._educational_load.clicked.connect(self._load_educational_lesson)
        educational_layout.addWidget(self._educational_load)
        self._educational_action = QPushButton(
            self._translator.text("desktop.educational.start")
        )
        self._educational_action.setEnabled(False)
        self._educational_action.clicked.connect(self._toggle_educational)
        educational_layout.addWidget(self._educational_action)
        lesson_navigation = QHBoxLayout()
        self._educational_previous = QPushButton(
            self._translator.text("desktop.educational.previous")
        )
        self._educational_next = QPushButton(
            self._translator.text("desktop.educational.next")
        )
        self._educational_restart = QPushButton(
            self._translator.text("desktop.educational.restart")
        )
        self._educational_previous.clicked.connect(
            lambda: self._educational_step("previous")
        )
        self._educational_next.clicked.connect(lambda: self._educational_step("next"))
        self._educational_restart.clicked.connect(
            lambda: self._educational_step("home")
        )
        self._educational_previous.setEnabled(False)
        self._educational_next.setEnabled(False)
        self._educational_restart.setEnabled(False)
        lesson_navigation.addWidget(self._educational_previous)
        lesson_navigation.addWidget(self._educational_next)
        educational_layout.addLayout(lesson_navigation)
        educational_layout.addWidget(self._educational_restart)
        inspector_layout.addWidget(educational)
        inspector_scroll = QScrollArea()
        inspector_scroll.setWidgetResizable(True)
        inspector_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        inspector_scroll.setMinimumWidth(240)
        inspector_scroll.setMaximumWidth(340)
        inspector_scroll.setWidget(inspector)
        layout.addWidget(inspector_scroll)
        for sequence, action in (
            ("Alt+Left", "previous"),
            ("Alt+Right", "next"),
            ("Alt+Home", "home"),
        ):
            shortcut = QShortcut(QKeySequence(sequence), root)
            shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            shortcut.activated.connect(
                lambda selected=action: self._educational_step(selected)
            )
            self._educational_shortcuts.append(shortcut)
        self.setCentralWidget(root)
        self._source.completed.connect(self._build_freehand)
        self._source.changed.connect(self._capture_changed)
        self._canvas.harmonic_selected.connect(self._canvas_harmonic_selected)
        self._basis_changed()
        self._set_status(self._translator.text("desktop.status.initial"))

    def _capture_changed(self, snapshot: object) -> None:
        count = len(getattr(snapshot, "points", ()))
        state = getattr(snapshot, "state", None)
        self._basis_selector.setEnabled(
            state is CaptureState.EMPTY
            and self._job is None
            and not self._playground_active
        )
        self._set_status(self._translator.text("desktop.status.captured", count=count))

    def _selected_basis(self) -> BasisKind:
        try:
            return BasisKind(str(self._basis_selector.currentData()))
        except ValueError as error:
            raise DomainValidationError("desktop basis selection is invalid") from error

    def _toggle_playground(self) -> None:
        if self._playground_active:
            self._exit_playground()
            return
        if (
            self._job is not None
            or self._solo.active
            or self._build_up.active
            or self._educational.active
        ):
            self._set_status(self._translator.text("desktop.playground.unavailable"))
            return
        baseline = self._timeline or self._haar_timeline
        if baseline is None:
            baseline = getattr(self, "_indexed_timeline", None)
        self._playground_baseline = baseline
        self._playground_baseline_basis = self._selected_basis()
        self._playground_baseline_visibility = {
            field: toggle.isChecked()
            for field, toggle in self._visibility_toggles.items()
        }
        self._playground_baseline_view = (
            self._canvas.view_zoom,
            self._canvas.view_pan,
            self._canvas.reference_view_size,
        )
        self._playground.reset_circle()
        blocked = self._basis_selector.blockSignals(True)
        self._basis_selector.setCurrentIndex(
            self._basis_selector.findData(BasisKind.FOURIER_EPICYCLE.value)
        )
        self._basis_selector.blockSignals(blocked)
        self._playground_active = True
        self._apply_playground_timeline()
        self._refresh_playground_controls()

    def _exit_playground(self) -> None:
        baseline = self._playground_baseline
        basis = self._playground_baseline_basis
        visibility = self._playground_baseline_visibility
        view = self._playground_baseline_view
        self._playground_active = False
        self._playground_baseline = None
        self._playground_baseline_basis = None
        self._playground_baseline_visibility = None
        self._playground_baseline_view = None
        self._timer.stop()
        if baseline is None:
            self._clear_displayed_result()
        else:
            self._apply_basis_timeline(baseline, preserve_timeline_state=True)
        if basis is not None:
            blocked = self._basis_selector.blockSignals(True)
            self._basis_selector.setCurrentIndex(
                self._basis_selector.findData(basis.value)
            )
            self._basis_selector.blockSignals(blocked)
        if visibility is not None and isinstance(
            baseline, (HaarTimeline, IndexedBasisTimeline)
        ):
            for field in ("original", "reconstruction"):
                enabled = visibility[field]
                toggle = self._visibility_toggles[field]
                blocked = toggle.blockSignals(True)
                toggle.setChecked(enabled)
                toggle.blockSignals(blocked)
                self._canvas.set_haar_visibility(field, enabled)
        if view is not None:
            self._canvas.restore_view_state(*view)
        self._source.setEnabled(True)
        self._basis_changed()
        self._refresh_playground_controls()
        self._set_status(self._translator.text("desktop.playground.exited"))

    def _apply_playground_timeline(self) -> None:
        view = (
            self._canvas.view_zoom,
            self._canvas.view_pan,
            self._canvas.reference_view_size,
        )
        timeline = self._playground.build_timeline(
            speed=self._speed.value() / _SPEED_SCALE
        )
        self._apply_timeline(timeline)
        self._apply_frame(timeline.set_visibility(original=False))
        self._canvas.restore_view_state(*view)
        self._set_status(
            self._translator.text(
                "desktop.playground.status",
                count=len(self._playground.components),
                total_amplitude=sum(
                    component.amplitude for component in self._playground.components
                ),
            )
        )
        self._refresh_playground_controls()

    def _apply_playground_component(self) -> None:
        if not self._playground_active:
            return
        before = self._playground.components
        try:
            self._playground.upsert(
                ManualHarmonic(
                    frequency=self._playground_frequency.value(),
                    amplitude=self._playground_amplitude.value(),
                    phase=radians(self._playground_phase.value()),
                )
            )
            self._apply_playground_timeline()
        except DomainValidationError:
            self._playground = HarmonicPlaygroundSession(before)
            self._set_status(self._translator.text("desktop.playground.invalid"))
            self._refresh_playground_controls()

    def _remove_playground_component(self) -> None:
        if not self._playground_active:
            return
        row = self._playground_list.currentRow()
        if row < 0 or row >= len(self._playground.components):
            return
        before = self._playground.components
        try:
            self._playground.remove(before[row].frequency)
            if self._playground.components:
                self._apply_playground_timeline()
            else:
                self._clear_playground_display()
        except DomainValidationError:
            self._playground = HarmonicPlaygroundSession(before)
            self._set_status(self._translator.text("desktop.playground.invalid"))
        self._refresh_playground_controls()

    def _clear_playground(self) -> None:
        if not self._playground_active:
            return
        self._playground.clear()
        self._clear_playground_display()
        self._refresh_playground_controls()

    def _clear_playground_display(self) -> None:
        self._timer.stop()
        self._timeline = None
        self._baseline_frame = None
        self._current_frame = None
        self._canvas.set_frame(None)
        self._reset_harmonic_inspector()
        self._sync_playground_locks()
        self._set_status(self._translator.text("desktop.playground.empty"))

    def _reset_playground_circle(self) -> None:
        if not self._playground_active:
            return
        self._playground.reset_circle()
        self._apply_playground_timeline()

    def _playground_row_changed(self, row: int) -> None:
        components = self._playground.components
        if row < 0 or row >= len(components):
            return
        component = components[row]
        self._playground_frequency.setValue(component.frequency)
        self._playground_amplitude.setValue(component.amplitude)
        self._playground_phase.setValue(degrees(component.phase))

    def _refresh_playground_controls(self) -> None:
        if not hasattr(self, "_playground_list"):
            return
        selected_frequency = None
        row = self._playground_list.currentRow()
        if 0 <= row < len(self._playground.components):
            selected_frequency = self._playground.components[row].frequency
        blocked = self._playground_list.blockSignals(True)
        self._playground_list.clear()
        selected_row = -1
        for index, component in enumerate(self._playground.components):
            self._playground_list.addItem(
                self._translator.text(
                    "desktop.playground.row",
                    position=index + 1,
                    frequency=component.frequency,
                    amplitude=component.amplitude,
                    phase=degrees(component.phase),
                )
            )
            if component.frequency == selected_frequency:
                selected_row = index
        if selected_row < 0 and self._playground.components:
            selected_row = 0
        self._playground_list.setCurrentRow(selected_row)
        self._playground_list.blockSignals(blocked)
        if selected_row >= 0:
            self._playground_row_changed(selected_row)
        active = self._playground_active
        self._playground_toggle.setText(
            self._translator.text(
                "desktop.playground.exit" if active else "desktop.playground.enter"
            )
        )
        self._playground_mode.setText(
            self._translator.text(
                "desktop.playground.active" if active else "desktop.playground.inactive",
                count=len(self._playground.components),
            )
        )
        self._playground_list.setEnabled(active)
        self._playground_frequency.setEnabled(active)
        self._playground_amplitude.setEnabled(active)
        self._playground_phase.setEnabled(active)
        self._playground_apply.setEnabled(active)
        self._playground_remove.setEnabled(active and selected_row >= 0)
        self._playground_clear.setEnabled(active and bool(self._playground.components))
        self._playground_reset.setEnabled(active)

    def _sync_playground_locks(self) -> None:
        if not self._playground_active:
            return
        self._basis_selector.setEnabled(False)
        self._source.setEnabled(False)
        self._image_button.setEnabled(False)
        self._harmonics.setEnabled(False)
        self._solo_action.setEnabled(False)
        self._build_up_action.setEnabled(False)
        self._build_up_ordering.setEnabled(False)
        self._build_up_target.setEnabled(False)
        self._build_up_dwell.setEnabled(False)
        self._educational_action.setEnabled(False)
        self._educational_load.setEnabled(False)
        self._export_nav.setEnabled(False)
        original = self._visibility_toggles["original"]
        blocked = original.blockSignals(True)
        original.setChecked(False)
        original.setEnabled(False)
        original.blockSignals(blocked)

    def _basis_changed(self) -> None:
        try:
            selected = self._selected_basis()
        except DomainValidationError:
            selected = BasisKind.HAAR_WAVELET
        non_fourier = selected is not BasisKind.FOURIER_EPICYCLE
        disabled_key = (
            "basis.haar.frequency_controls_disabled"
            if selected is BasisKind.HAAR_WAVELET
            else f"basis.{selected.value}.frequency_controls_disabled"
        )
        self._image_button.setEnabled(
            not non_fourier and self._job is None and not self._playground_active
        )
        self._image_button.setToolTip(
            self._translator.text(disabled_key) if non_fourier else ""
        )
        if hasattr(self, "_educational_load"):
            self._educational_load.setEnabled(
                not non_fourier
                and not self._educational.active
                and not self._playground_active
            )

    def _reset_source(self) -> None:
        if self._playground_active:
            self._set_status(self._translator.text("desktop.playground.unavailable"))
            return
        self._timer.stop()
        if self._job is not None:
            self._cancel_current_job()
        self._source.reset()
        self._timeline = None
        self._haar_timeline = None
        self._indexed_timeline = None
        self._solo.clear()
        self._build_up.clear()
        self._educational.clear()
        self._educational_lesson = None
        self._educational_snapshot = None
        self._solo_mode.setText(self._translator.text("desktop.solo.inactive"))
        self._build_up_mode.setText(self._translator.text("desktop.build_up.inactive"))
        self._educational_mode.setText(
            self._translator.text("desktop.educational.unavailable")
        )
        self._educational_body.setText("")
        self._educational_equation.setText("")
        self._reset_harmonic_inspector()
        self._canvas.set_frame(None)
        self._canvas.reset_view()
        self._harmonics.setRange(1, 1)
        self._harmonics.setValue(1)
        self._term_label.setText(self._translator.text("control.harmonics"))
        self._export_nav.setEnabled(False)
        for toggle in self._visibility_toggles.values():
            blocked = toggle.blockSignals(True)
            toggle.setChecked(False)
            toggle.setEnabled(False)
            toggle.blockSignals(blocked)
        self._basis_selector.setEnabled(self._job is None)
        self._basis_changed()

    def _build_freehand(self, snapshot: object) -> None:
        points = tuple(getattr(snapshot, "points", ()))
        if not points:
            return
        reference_view_size = (float(self._source.width()), float(self._source.height()))
        try:
            basis = self._selected_basis()
        except DomainValidationError:
            self._set_status(self._translator.text("desktop.status.invalid_control"))
            return
        self._clear_displayed_result()

        def operation() -> EpicycleTimeline | HaarTimeline | IndexedBasisTimeline:
            curve = Curve(points, closed=False)
            return build_basis_timeline(
                curve,
                basis=basis,
                speed=self._speed.value() / _SPEED_SCALE,
            )

        self._start_job(
            operation,
            lambda result: self._apply_basis_timeline(
                result, reference_view_size=reference_view_size
            ),
            failure_key=(
                "basis.haar.invalid"
                if basis is BasisKind.HAAR_WAVELET
                else (
                    "basis.indexed.invalid"
                    if basis in {BasisKind.DCT_II, BasisKind.WALSH_HADAMARD}
                    else "desktop.status.runtime"
                )
            ),
        )

    def _clear_displayed_result(self) -> None:
        """Remove an older basis result before publishing a new source result."""

        self._timer.stop()
        self._timeline = None
        self._haar_timeline = None
        self._indexed_timeline = None
        self._solo.clear()
        self._build_up.clear()
        self._educational.clear()
        self._educational_lesson = None
        self._educational_snapshot = None
        self._reset_harmonic_inspector()
        self._canvas.set_frame(None)
        self._export_nav.setEnabled(False)
        for toggle in self._visibility_toggles.values():
            blocked = toggle.blockSignals(True)
            toggle.setChecked(False)
            toggle.setEnabled(False)
            toggle.blockSignals(blocked)

    def _choose_image(self) -> None:
        selected = self._selected_basis()
        if selected is not BasisKind.FOURIER_EPICYCLE or self._playground_active:
            self._set_status(
                self._translator.text(
                    "desktop.playground.unavailable"
                    if self._playground_active
                    else f"basis.{selected.value}.frequency_controls_disabled"
                )
            )
            return
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
        failure_key: str = "desktop.status.runtime",
    ) -> None:
        if self._job is not None and self._job.isRunning():
            self._set_status(self._translator.text("desktop.status.busy"))
            return
        self._job_generation += 1
        generation = self._job_generation
        self._job = _Job(operation)
        self._basis_selector.setEnabled(False)
        self._cancel.setEnabled(True)

        def on_job_success(result: object, expected: int = generation) -> None:
            if self._job_generation != expected:
                return
            on_success(result)

        def on_job_failed(_key: str, expected: int = generation) -> None:
            if self._job_generation != expected:
                return
            self._set_status(self._translator.text(failure_key))

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
        if self._haar_timeline is not None or self._indexed_timeline is not None:
            if field in {"original", "reconstruction"}:
                try:
                    self._canvas.set_haar_visibility(field, enabled)
                except DomainValidationError:
                    self._set_status(
                        self._translator.text("desktop.status.invalid_control")
                    )
            return
        timeline = self._timeline
        if timeline is None or self._build_up.active:
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
        self._basis_selector.setEnabled(
            self._source._capture.snapshot().state is CaptureState.EMPTY
            and self._timeline is None
            and self._haar_timeline is None
            and self._indexed_timeline is None
            and not self._playground_active
        )
        self._basis_changed()
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
        educational_lesson: CanonicalCircleLesson | None = None,
        preserve_timeline_state: bool = False,
    ) -> None:
        if not isinstance(timeline, EpicycleTimeline):
            self._set_status(self._translator.text("desktop.status.runtime"))
            return
        self._haar_timeline = None
        self._indexed_timeline = None
        self._solo.clear()
        self._build_up.clear()
        self._build_up_snapshot = None
        self._build_up_restore_frequency = None
        self._educational.clear()
        self._educational_snapshot = None
        self._educational_lesson = educational_lesson
        self._canvas.set_educational_sample(None)
        self._reset_harmonic_inspector()
        self._timeline = timeline
        self._basis_selector.setEnabled(False)
        self._term_label.setText(self._translator.text("control.harmonics"))
        self._canvas.set_reference_view_size(reference_view_size)
        self._canvas.reset_view()
        for toggle in self._visibility_toggles.values():
            blocked = toggle.blockSignals(True)
            toggle.setChecked(True)
            toggle.setEnabled(True)
            toggle.blockSignals(blocked)
        self._export_nav.setEnabled(True)
        self._build_up_target.setRange(1, timeline.maximum_harmonics)
        self._build_up_target.setValue(timeline.harmonic_count)
        self._export_format_changed()
        if preserve_timeline_state:
            self._apply_frame(timeline.snapshot())
            if timeline.state is TimelineState.RUNNING:
                self._last_tick = monotonic()
                self._timer.start()
        else:
            speed = self._speed.value() / _SPEED_SCALE
            self._apply_frame(timeline.set_speed(speed))

    def _apply_basis_timeline(
        self,
        timeline: object,
        *,
        reference_view_size: tuple[float, float] | None = None,
        preserve_timeline_state: bool = False,
    ) -> None:
        if isinstance(timeline, EpicycleTimeline):
            self._apply_timeline(
                timeline,
                reference_view_size=reference_view_size,
                preserve_timeline_state=preserve_timeline_state,
            )
            return
        if isinstance(timeline, HaarTimeline):
            self._apply_haar_timeline(
                timeline,
                reference_view_size=reference_view_size,
                preserve_timeline_state=preserve_timeline_state,
            )
            return
        if isinstance(timeline, IndexedBasisTimeline):
            self._apply_indexed_timeline(
                timeline,
                reference_view_size=reference_view_size,
                preserve_timeline_state=preserve_timeline_state,
            )
            return
        self._set_status(self._translator.text("desktop.status.runtime"))

    def _apply_haar_timeline(
        self,
        timeline: HaarTimeline,
        *,
        reference_view_size: tuple[float, float] | None = None,
        preserve_timeline_state: bool = False,
    ) -> None:
        self._timer.stop()
        self._timeline = None
        self._indexed_timeline = None
        self._haar_timeline = timeline
        self._basis_selector.setEnabled(False)
        self._solo.clear()
        self._build_up.clear()
        self._build_up_snapshot = None
        self._build_up_restore_frequency = None
        self._educational.clear()
        self._educational_snapshot = None
        self._educational_lesson = None
        unavailable = self._translator.text(
            "basis.haar.frequency_controls_disabled"
        )
        self._solo_mode.setText(unavailable)
        self._build_up_mode.setText(unavailable)
        self._educational_mode.setText(unavailable)
        self._educational_body.setText("")
        self._educational_equation.setText("")
        self._reset_harmonic_inspector()
        self._canvas.set_reference_view_size(reference_view_size)
        self._canvas.reset_view()
        self._term_label.setText(self._translator.text("control.terms"))
        self._export_nav.setEnabled(False)
        self._export_nav.setToolTip(
            self._translator.text("basis.haar.frequency_controls_disabled")
        )
        for field, toggle in self._visibility_toggles.items():
            available = field in {"original", "reconstruction"}
            toggle_blocked = toggle.blockSignals(True)
            toggle.setChecked(available)
            toggle.setEnabled(available)
            toggle.blockSignals(toggle_blocked)
            if available:
                self._canvas.set_haar_visibility(field, True)
        self._apply_haar_frame(timeline.snapshot())
        if preserve_timeline_state and timeline.state is TimelineState.RUNNING:
            self._last_tick = monotonic()
            self._timer.start()

    def _apply_haar_frame(self, frame: object) -> None:
        if not isinstance(frame, HaarFrame):
            self._set_status(self._translator.text("desktop.status.runtime"))
            return
        self._canvas.set_haar_frame(frame)
        blocked = self._harmonics.blockSignals(True)
        self._harmonics.setRange(1, frame.total_terms)
        self._harmonics.setValue(frame.term_count)
        self._harmonics.blockSignals(blocked)
        self._harmonics.setEnabled(True)
        self._inspector_list.setEnabled(False)
        self._solo_action.setEnabled(False)
        self._build_up_action.setEnabled(False)
        self._build_up_ordering.setEnabled(False)
        self._build_up_target.setEnabled(False)
        self._build_up_dwell.setEnabled(False)
        self._educational_action.setEnabled(False)
        self._educational_load.setEnabled(False)
        self._export_nav.setEnabled(False)
        active = frame.active_term
        if active.kind.value == "scaling":
            key = "basis.haar.single_term"
            values: dict[str, object] = {}
        else:
            key = "basis.haar.status"
            values = {
                "kind": active.kind.value,
                "level": active.scale,
                "location": active.location,
            }
        self._set_status(
            self._translator.text(
                key,
                state=frame.state,
                selected=frame.term_count,
                total=frame.total_terms,
                speed=frame.speed,
                **values,
            )
        )

    def _apply_indexed_timeline(
        self,
        timeline: IndexedBasisTimeline,
        *,
        reference_view_size: tuple[float, float] | None = None,
        preserve_timeline_state: bool = False,
    ) -> None:
        self._timer.stop()
        self._timeline = None
        self._haar_timeline = None
        self._indexed_timeline = timeline
        self._basis_selector.setEnabled(False)
        self._solo.clear()
        self._build_up.clear()
        self._build_up_snapshot = None
        self._build_up_restore_frequency = None
        self._educational.clear()
        self._educational_snapshot = None
        self._educational_lesson = None
        unavailable = self._translator.text(
            f"basis.{timeline.basis.value}.frequency_controls_disabled"
        )
        self._solo_mode.setText(unavailable)
        self._build_up_mode.setText(unavailable)
        self._educational_mode.setText(unavailable)
        self._educational_body.setText("")
        self._educational_equation.setText("")
        self._reset_harmonic_inspector()
        self._canvas.set_reference_view_size(reference_view_size)
        self._canvas.reset_view()
        self._term_label.setText(self._translator.text("control.terms"))
        self._export_nav.setEnabled(False)
        self._export_nav.setToolTip(unavailable)
        for field, toggle in self._visibility_toggles.items():
            available = field in {"original", "reconstruction"}
            blocked = toggle.blockSignals(True)
            toggle.setChecked(available)
            toggle.setEnabled(available)
            toggle.blockSignals(blocked)
            if available:
                self._canvas.set_haar_visibility(field, True)
        self._apply_indexed_frame(timeline.snapshot())
        if preserve_timeline_state and timeline.state is TimelineState.RUNNING:
            self._last_tick = monotonic()
            self._timer.start()

    def _apply_indexed_frame(self, frame: object) -> None:
        if not isinstance(frame, IndexedBasisFrame):
            self._set_status(self._translator.text("desktop.status.runtime"))
            return
        self._canvas.set_indexed_basis_frame(frame)
        blocked = self._harmonics.blockSignals(True)
        self._harmonics.setRange(1, frame.total_terms)
        self._harmonics.setValue(frame.term_count)
        self._harmonics.blockSignals(blocked)
        self._harmonics.setEnabled(True)
        self._inspector_list.setEnabled(False)
        self._solo_action.setEnabled(False)
        self._build_up_action.setEnabled(False)
        self._build_up_ordering.setEnabled(False)
        self._build_up_target.setEnabled(False)
        self._build_up_dwell.setEnabled(False)
        self._educational_action.setEnabled(False)
        self._educational_load.setEnabled(False)
        self._export_nav.setEnabled(False)
        self._set_status(
            self._translator.text(
                f"basis.{frame.basis.value}.status",
                state=frame.state,
                selected=frame.term_count,
                total=frame.total_terms,
                index=frame.active_term.index,
                speed=frame.speed,
            )
        )

    def _export_format_changed(self) -> None:
        export_format = self._selected_export_format()
        is_mp4 = export_format is ExportFormat.MP4
        analysis_active = (
            self._solo.active
            or self._build_up.active
            or self._educational.active
            or self._playground_active
        )
        self._export_action.setEnabled(
            self._timeline is not None and not is_mp4 and not analysis_active
        )
        self._export_frames.setEnabled(export_format is ExportFormat.GIF)
        self._export_duration.setEnabled(export_format is ExportFormat.GIF)
        if self._build_up.active:
            self._export_action.setToolTip(
                self._translator.text("desktop.build_up.export_disabled")
            )
        elif self._solo.active:
            self._export_action.setToolTip(
                self._translator.text("desktop.solo.export_disabled")
            )
        elif is_mp4:
            self._export_action.setToolTip(mp4_capability().reason)
            self._set_status(self._translator.text("desktop.export.mp4_unavailable"))
        else:
            self._export_action.setToolTip("")

    def _choose_export(self) -> None:
        timeline = self._timeline
        export_format = self._selected_export_format()
        if (
            timeline is None
            or self._solo.active
            or self._build_up.active
            or self._playground_active
        ):
            if self._build_up.active:
                self._set_status(
                    self._translator.text("desktop.build_up.export_disabled")
                )
            elif self._solo.active:
                self._set_status(self._translator.text("desktop.solo.export_disabled"))
            elif self._playground_active:
                self._set_status(
                    self._translator.text("desktop.playground.export_disabled")
                )
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
        self._baseline_frame = frame
        try:
            display_frame = self._solo.project(frame, source=self._timeline)
            build_snapshot = self._build_up.project(frame, source=self._timeline)
            if build_snapshot is not None:
                display_frame = build_snapshot.frame
                self._selected_harmonic_frequency = (
                    build_snapshot.metrics.latest_frequency
                )
            educational_snapshot = self._project_educational(frame)
            if educational_snapshot is not None:
                self._selected_harmonic_frequency = CANONICAL_CIRCLE_FREQUENCY
        except DomainValidationError:
            self._solo.clear()
            self._build_up.clear()
            self._educational.clear()
            display_frame = frame
            build_snapshot = None
            educational_snapshot = None
            self._set_status(self._translator.text("desktop.status.invalid_control"))
        self._build_up_snapshot = build_snapshot
        self._educational_snapshot = educational_snapshot
        self._current_frame = display_frame
        self._canvas.set_frame(display_frame)
        self._sync_harmonic_inspector(display_frame if build_snapshot is not None else frame)
        for field, toggle in self._visibility_toggles.items():
            blocked = toggle.blockSignals(True)
            toggle.setChecked(bool(getattr(frame.visibility, field)))
            toggle.setEnabled(True)
            toggle.blockSignals(blocked)
        harmonics_blocked = self._harmonics.blockSignals(True)
        self._harmonics.setRange(1, frame.selection.sample_count)
        self._harmonics.setValue(frame.selection.coefficient_count)
        self._harmonics.blockSignals(harmonics_blocked)
        self._sync_solo_controls(frame)
        self._sync_build_up_controls(build_snapshot)
        self._sync_educational_controls(educational_snapshot)
        self._set_status(
            self._translator.text(
                "status.summary",
                state=frame.timeline_state,
                time=display_frame.chain.time,
                harmonics=display_frame.selection.coefficient_count,
                speed=display_frame.speed,
            )
        )
        self._sync_playground_locks()

    def _reset_harmonic_inspector(self) -> None:
        self._selected_harmonic_frequency = None
        self._baseline_frame = None
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
        self._inspector_list.setEnabled(
            not self._solo.active and not self._educational.active
        )

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
        if self._solo.active or self._build_up.active or self._educational.active:
            return
        self._selected_harmonic_frequency = frequency
        frame = self._current_frame
        if frame is None:
            self._reset_harmonic_inspector()
            return
        self._sync_harmonic_inspector(frame)
        baseline = self._baseline_frame
        if baseline is not None:
            self._sync_solo_controls(baseline)

    def _canvas_harmonic_selected(self, value: object) -> None:
        frequency = value if type(value) is int else None
        self._select_harmonic(frequency)

    def _load_educational_lesson(self) -> None:
        if (
            self._job is not None
            or self._educational.active
            or self._selected_basis() is not BasisKind.FOURIER_EPICYCLE
            or self._playground_active
        ):
            return
        try:
            lesson = build_canonical_circle_lesson()
            self._apply_timeline(lesson.timeline, educational_lesson=lesson)
            self._set_status(self._translator.text("desktop.educational.ready"))
        except DomainValidationError:
            self._educational_lesson = None
            self._set_status(self._translator.text("desktop.educational.invalid"))
            self._sync_educational_controls(None)

    def _project_educational(self, frame: EpicycleFrame) -> EducationalSnapshot | None:
        lesson = self._educational_lesson
        timeline = self._timeline
        if not self._educational.active:
            return None
        if lesson is None or timeline is None:
            self._educational.clear()
            return None
        projection = self._educational.project(
            frame,
            spectrum=timeline.complete_spectrum,
            source=lesson,
            lesson_id=lesson.lesson_id,
        )
        if isinstance(projection, EducationalUnavailable):
            self._set_status(self._translator.text("desktop.educational.invalid"))
            return None
        return projection

    def _toggle_educational(self) -> None:
        timeline = self._timeline
        lesson = self._educational_lesson
        baseline = self._baseline_frame
        if timeline is None or lesson is None or baseline is None:
            return
        try:
            if self._educational.active:
                self._educational.clear()
                self._educational_snapshot = None
                self._canvas.set_educational_sample(None)
                self._selected_harmonic_frequency = None
                self._apply_frame(timeline.snapshot())
                return
            if (
                self._solo.active
                or self._build_up.active
                or self._playground_active
                or timeline is not lesson.timeline
            ):
                raise DomainValidationError("Educational Mode requires its canonical timeline")
            if timeline.state is TimelineState.RUNNING:
                baseline = timeline.pause()
                self._timer.stop()
            projection = self._educational.enter(
                baseline,
                spectrum=timeline.complete_spectrum,
                source=lesson,
                lesson_id=lesson.lesson_id,
            )
            if isinstance(projection, EducationalUnavailable):
                raise DomainValidationError("Educational Mode projection is unavailable")
            self._selected_harmonic_frequency = CANONICAL_CIRCLE_FREQUENCY
            self._apply_frame(baseline)
        except DomainValidationError:
            self._educational.clear()
            self._educational_snapshot = None
            self._canvas.set_educational_sample(None)
            self._set_status(self._translator.text("desktop.educational.invalid"))
            self._sync_educational_controls(None)

    def _educational_step(self, action: str) -> None:
        if not self._educational.active:
            return
        timeline = self._timeline
        if timeline is None:
            return
        try:
            operation = {
                "previous": self._educational.previous,
                "next": self._educational.next,
                "home": self._educational.home,
            }.get(action)
            if operation is None:
                return
            operation()
            self._apply_frame(timeline.snapshot())
        except DomainValidationError:
            self._educational.clear()
            self._educational_snapshot = None
            self._canvas.set_educational_sample(None)
            self._set_status(self._translator.text("desktop.educational.invalid"))

    def _sync_educational_controls(
        self, snapshot: EducationalSnapshot | None
    ) -> None:
        lesson_ready = (
            self._educational_lesson is not None
            and self._timeline is self._educational_lesson.timeline
        )
        if self._educational.active and snapshot is not None:
            active = True
            copy = format_educational_copy(snapshot, self._translator)
            self._educational_mode.setText(
                self._translator.text(
                    "desktop.educational.active",
                    current=snapshot.step_index + 1,
                    total=snapshot.step_count,
                    title=copy.title,
                )
            )
            self._educational_body.setText(copy.body)
            self._educational_equation.setText(copy.equation)
            action_text = self._translator.text("desktop.educational.exit")
            self._canvas.set_educational_sample(
                snapshot.sample if snapshot.step.value == "samples" else None
            )
        else:
            active = False
            action_text = self._translator.text("desktop.educational.start")
            self._educational_mode.setText(
                self._translator.text(
                    "desktop.educational.ready"
                    if lesson_ready
                    else "desktop.educational.unavailable"
                )
            )
            self._educational_body.setText("")
            self._educational_equation.setText("")
            self._canvas.set_educational_sample(None)
        self._educational_action.setText(action_text)
        self._educational_action.setAccessibleName(action_text)
        self._educational_action.setEnabled(
            active
            or (
                lesson_ready
                and not self._solo.active
                and not self._build_up.active
            )
        )
        self._educational_load.setEnabled(not active and self._job is None)
        step_index = snapshot.step_index if snapshot is not None else 0
        step_count = snapshot.step_count if snapshot is not None else 0
        self._educational_previous.setEnabled(active and step_index > 0)
        self._educational_next.setEnabled(
            active and step_index + 1 < step_count
        )
        self._educational_restart.setEnabled(active and step_index > 0)
        baseline_controls_enabled = (
            not active and not self._solo.active and not self._build_up.active
        )
        self._harmonics.setEnabled(baseline_controls_enabled)
        self._inspector_list.setEnabled(baseline_controls_enabled)
        self._export_nav.setEnabled(
            self._timeline is not None
            and not active
            and not self._solo.active
            and not self._build_up.active
        )
        self._export_nav.setToolTip(
            self._translator.text("desktop.educational.export_disabled") if active else ""
        )
        self._export_format_changed()

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

    def _toggle_solo(self) -> None:
        if self._playground_active:
            self._set_status(self._translator.text("desktop.playground.unavailable"))
            return
        timeline = self._timeline
        if timeline is None:
            return
        baseline = self._baseline_frame
        if baseline is None:
            return
        try:
            if self._solo.active:
                self._solo.exit(baseline, source=timeline)
            else:
                if self._educational.active:
                    raise DomainValidationError("Solo cannot start during Educational Mode")
                frequency = self._selected_harmonic_frequency
                if frequency is None:
                    raise DomainValidationError("frequency Solo requires a selection")
                self._solo.enter(baseline, frequency, source=timeline)
            self._apply_frame(baseline)
        except DomainValidationError:
            self._set_status(self._translator.text("desktop.solo.requires_selection"))

    def _sync_solo_controls(self, _frame: EpicycleFrame) -> None:
        active = self._solo.active
        build_active = self._build_up.active or self._educational.active
        frequency = self._solo.frequency
        if active and frequency is not None:
            action_text = self._translator.text("desktop.solo.exit")
            self._solo_mode.setText(
                self._translator.text("desktop.solo.active", frequency=frequency)
            )
        else:
            action_text = self._translator.text("desktop.solo.enter")
            self._solo_mode.setText(self._translator.text("desktop.solo.inactive"))
        self._solo_action.setText(action_text)
        self._solo_action.setAccessibleName(action_text)
        self._solo_action.setEnabled(
            not build_active and (active or self._selected_harmonic_frequency is not None)
        )
        self._harmonics.setEnabled(not active and not build_active)
        self._inspector_list.setEnabled(not active and not build_active)
        self._export_nav.setEnabled(
            self._timeline is not None and not active and not build_active
        )
        self._export_nav.setToolTip(
            self._translator.text("desktop.build_up.export_disabled")
            if build_active
            else self._translator.text("desktop.solo.export_disabled")
            if active
            else ""
        )
        self._export_format_changed()

    def _toggle_build_up(self) -> None:
        if self._playground_active:
            self._set_status(self._translator.text("desktop.playground.unavailable"))
            return
        timeline = self._timeline
        baseline = self._baseline_frame
        if timeline is None or baseline is None:
            return
        try:
            if self._build_up.active:
                self._build_up.exit(baseline, source=timeline)
                restore = self._build_up_restore_frequency
                self._build_up_restore_frequency = None
                self._selected_harmonic_frequency = (
                    restore if restore in baseline.selection.frequencies else None
                )
                self._last_tick = monotonic()
                if timeline.state is TimelineState.RUNNING:
                    self._timer.start()
                else:
                    self._timer.stop()
            else:
                if self._solo.active or self._educational.active:
                    raise DomainValidationError("Build-Up cannot start during Solo")
                self._build_up_restore_frequency = self._selected_harmonic_frequency
                ordering = SpectrumOrdering(str(self._build_up_ordering.currentData()))
                snapshot = self._build_up.enter(
                    baseline,
                    spectrum=timeline.complete_spectrum,
                    source=timeline,
                    ordering=ordering,
                    target_count=self._build_up_target.value(),
                    dwell_seconds=self._build_up_dwell.value() / 1000.0,
                )
                self._selected_harmonic_frequency = snapshot.metrics.latest_frequency
                self._last_tick = monotonic()
                if snapshot.state is BuildUpState.RUNNING:
                    self._timer.start()
                else:
                    self._timer.stop()
            self._apply_frame(baseline)
        except (DomainValidationError, ValueError):
            self._set_status(self._translator.text("desktop.build_up.invalid"))

    def _sync_build_up_controls(self, snapshot: BuildUpSnapshot | None) -> None:
        active = self._build_up.active
        solo_active = self._solo.active or self._educational.active
        if active and snapshot is not None:
            action_text = self._translator.text("desktop.build_up.exit")
            self._build_up_mode.setText(
                self._translator.text(
                    "desktop.build_up.active",
                    state=snapshot.state,
                    ordering=self._translator.text(
                        f"desktop.build_up.ordering.{snapshot.ordering.value}"
                    ),
                    current=snapshot.metrics.current_count,
                    target=snapshot.metrics.target_count,
                    frequency=snapshot.metrics.latest_frequency,
                    dwell=snapshot.dwell_seconds,
                    energy=snapshot.metrics.retained_energy_ratio,
                    rmse=snapshot.metrics.reconstruction_metrics.rmse,
                )
            )
        else:
            action_text = self._translator.text("desktop.build_up.start")
            self._build_up_mode.setText(
                self._translator.text("desktop.build_up.inactive")
            )
        self._build_up_action.setText(action_text)
        self._build_up_action.setAccessibleName(action_text)
        self._build_up_action.setEnabled(active or (self._timeline is not None and not solo_active))
        configuration_enabled = not active and not solo_active and self._timeline is not None
        self._build_up_ordering.setEnabled(configuration_enabled)
        self._build_up_target.setEnabled(configuration_enabled)
        self._build_up_dwell.setEnabled(configuration_enabled)
        self._speed.setEnabled(not active)
        for toggle in self._visibility_toggles.values():
            toggle.setEnabled(self._timeline is not None and not active)

    def _timeline_action(self, action: str, value: float | int | None = None) -> None:
        indexed_timeline = self._indexed_timeline
        if indexed_timeline is not None:
            try:
                operation = {
                    "play": indexed_timeline.play,
                    "pause": indexed_timeline.pause,
                    "restart": indexed_timeline.restart,
                }.get(action)
                if operation is not None:
                    next_indexed_frame = operation()
                    if (
                        action == "play"
                        and next_indexed_frame.state is TimelineState.RUNNING
                    ):
                        self._last_tick = monotonic()
                        self._timer.start()
                    else:
                        self._timer.stop()
                elif action == "harmonics":
                    if value is None:
                        return
                    next_indexed_frame = indexed_timeline.set_term_count(int(value))
                    if next_indexed_frame.state is TimelineState.PAUSED:
                        self._timer.stop()
                elif action == "speed":
                    if value is None:
                        return
                    next_indexed_frame = indexed_timeline.set_speed(float(value))
                elif action == "advance":
                    if value is None:
                        return
                    next_indexed_frame = indexed_timeline.advance(float(value))
                    if next_indexed_frame.state is TimelineState.PAUSED:
                        self._timer.stop()
                else:
                    return
                self._apply_indexed_frame(next_indexed_frame)
            except DomainValidationError:
                self._set_status(self._translator.text("desktop.status.invalid_control"))
            return
        haar_timeline = self._haar_timeline
        if haar_timeline is not None:
            try:
                haar_operation = {
                    "play": haar_timeline.play,
                    "pause": haar_timeline.pause,
                    "restart": haar_timeline.restart,
                }.get(action)
                if haar_operation is not None:
                    next_haar_frame = haar_operation()
                    if action == "play" and next_haar_frame.state is TimelineState.RUNNING:
                        self._last_tick = monotonic()
                        self._timer.start()
                    else:
                        self._timer.stop()
                elif action == "harmonics":
                    if value is None:
                        return
                    next_haar_frame = haar_timeline.set_term_count(int(value))
                    if next_haar_frame.state is TimelineState.PAUSED:
                        self._timer.stop()
                elif action == "speed":
                    if value is None:
                        return
                    next_haar_frame = haar_timeline.set_speed(float(value))
                elif action == "advance":
                    if value is None:
                        return
                    next_haar_frame = haar_timeline.advance(float(value))
                    if next_haar_frame.state is TimelineState.PAUSED:
                        self._timer.stop()
                else:
                    return
                self._apply_haar_frame(next_haar_frame)
            except DomainValidationError:
                self._set_status(self._translator.text("desktop.status.invalid_control"))
            return
        timeline = self._timeline
        if timeline is None:
            return
        try:
            if self._build_up.active:
                baseline = self._baseline_frame
                if baseline is None:
                    return
                if action == "play":
                    self._build_up.play()
                    self._last_tick = monotonic()
                    if self._build_up.state is BuildUpState.RUNNING:
                        self._timer.start()
                elif action == "pause":
                    self._build_up.pause()
                    self._timer.stop()
                elif action == "restart":
                    self._build_up.restart()
                    self._timer.stop()
                elif action == "advance":
                    if value is None:
                        return
                    self._build_up.advance(float(value))
                    if self._build_up.state is BuildUpState.COMPLETED:
                        self._timer.stop()
                else:
                    return
                self._apply_frame(baseline)
                return
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
                if (
                    value is None
                    or self._solo.active
                    or self._build_up.active
                    or self._educational.active
                    or self._playground_active
                ):
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
        indexed_timeline = self._indexed_timeline
        if indexed_timeline is not None:
            if indexed_timeline.state is TimelineState.PAUSED:
                self._timer.stop()
                return
            now = monotonic()
            delta = now - self._last_tick
            self._last_tick = now
            self._timeline_action("advance", delta)
            return
        haar_timeline = self._haar_timeline
        if haar_timeline is not None:
            if haar_timeline.state is TimelineState.PAUSED:
                self._timer.stop()
                return
            now = monotonic()
            delta = now - self._last_tick
            self._last_tick = now
            self._timeline_action("advance", delta)
            return
        timeline = self._timeline
        if self._build_up.active:
            if self._build_up.state is not BuildUpState.RUNNING:
                self._timer.stop()
                return
            now = monotonic()
            delta = now - self._last_tick
            self._last_tick = now
            self._timeline_action("advance", delta)
            return
        if timeline is None or timeline.state is TimelineState.PAUSED:
            self._timer.stop()
            return
        now = monotonic()
        delta = now - self._last_tick
        self._last_tick = now
        self._timeline_action("advance", delta)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if self._educational.active and (
            event.modifiers() & Qt.KeyboardModifier.AltModifier
        ):
            educational_action = None
            if event.key() == Qt.Key.Key_Left:
                educational_action = "previous"
            elif event.key() == Qt.Key.Key_Right:
                educational_action = "next"
            elif event.key() == Qt.Key.Key_Home:
                educational_action = "home"
            if educational_action is not None:
                self._educational_step(educational_action)
                event.accept()
                return
        if event.key() == Qt.Key.Key_Escape:
            self._cancel_current_job()
            event.accept()
            return
        if event.key() == Qt.Key.Key_R:
            self._reset_source()
            event.accept()
            return
        if event.key() == Qt.Key.Key_Space:
            indexed_timeline = self._indexed_timeline
            if indexed_timeline is not None:
                action = (
                    "pause"
                    if indexed_timeline.state is TimelineState.RUNNING
                    else "play"
                )
                self._timeline_action(action)
                event.accept()
                return
            haar_timeline = self._haar_timeline
            if haar_timeline is not None:
                action = (
                    "pause"
                    if haar_timeline.state is TimelineState.RUNNING
                    else "play"
                )
                self._timeline_action(action)
                event.accept()
                return
            timeline = self._timeline
            if timeline is not None:
                if self._build_up.active:
                    action = (
                        "pause"
                        if self._build_up.state is BuildUpState.RUNNING
                        else "play"
                    )
                else:
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
