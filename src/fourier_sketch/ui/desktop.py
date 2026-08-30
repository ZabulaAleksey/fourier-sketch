"""Responsive PySide6 shell that only dispatches existing application use cases."""

from __future__ import annotations

from collections.abc import Callable
from math import isfinite
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
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QSlider,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from fourier_sketch.application import (
    CaptureState,
    EpicycleFrame,
    EpicycleTimeline,
    FreehandCapture,
    ImageMvpConfig,
    ImageMvpController,
    ImageMvpSnapshot,
    ImageMvpState,
    TimelineState,
    build_freehand_timeline,
)
from fourier_sketch.domain import Curve, DomainValidationError, Point2D
from fourier_sketch.imaging import ImagePreprocessingOptions
from fourier_sketch.presentation import Translator, resolve_locale


class _Job(QThread):
    """One bounded worker; it publishes only completed application snapshots."""

    finished_snapshot = Signal(object)
    failed = Signal(str)

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


_SPEED_MIN = 0.10
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


def _rainbow_color(selection_index: int) -> QColor:
    """Return a stable presentation color independent of the selected K."""

    hue = (selection_index * _RAINBOW_HUE_STEP) % 1.0
    return QColor.fromHsvF(hue, 0.78, 0.90)


def _bounded_view_zoom(zoom: float) -> float:
    if not isfinite(zoom):
        raise ValueError("view zoom must be finite")
    bounded = max(_VIEW_ZOOM_MIN, min(_VIEW_ZOOM_MAX, zoom))
    return round(bounded * _VIEW_ZOOM_SCALE) / _VIEW_ZOOM_SCALE


def _zoom_about_point(
    *,
    zoom: float,
    pan: tuple[float, float],
    anchor: tuple[float, float],
    viewport_center: tuple[float, float],
    requested_zoom: float,
) -> tuple[float, tuple[float, float]]:
    """Scale a presentation viewport while preserving the scene point at ``anchor``."""

    next_zoom = _bounded_view_zoom(requested_zoom)
    if next_zoom == zoom:
        return zoom, pan
    scale_ratio = next_zoom / zoom
    relative_x = anchor[0] - viewport_center[0] - pan[0]
    relative_y = anchor[1] - viewport_center[1] - pan[1]
    return next_zoom, (
        pan[0] + relative_x * (1.0 - scale_ratio),
        pan[1] + relative_y * (1.0 - scale_ratio),
    )


def _gesture_view_transform(
    *,
    zoom: float,
    pan: tuple[float, float],
    previous_points: tuple[tuple[float, float], ...],
    current_points: tuple[tuple[float, float], ...],
    viewport_center: tuple[float, float],
) -> tuple[float, tuple[float, float]]:
    """Compute one-finger pan or two-finger anchored pinch without product state."""

    if len(previous_points) != len(current_points):
        return zoom, pan
    if len(current_points) == 1:
        return zoom, (
            pan[0] + current_points[0][0] - previous_points[0][0],
            pan[1] + current_points[0][1] - previous_points[0][1],
        )
    if len(current_points) != 2:
        return zoom, pan

    previous_center = (
        (previous_points[0][0] + previous_points[1][0]) / 2.0,
        (previous_points[0][1] + previous_points[1][1]) / 2.0,
    )
    current_center = (
        (current_points[0][0] + current_points[1][0]) / 2.0,
        (current_points[0][1] + current_points[1][1]) / 2.0,
    )
    previous_dx = previous_points[1][0] - previous_points[0][0]
    previous_dy = previous_points[1][1] - previous_points[0][1]
    current_dx = current_points[1][0] - current_points[0][0]
    current_dy = current_points[1][1] - current_points[0][1]
    previous_distance = (previous_dx * previous_dx + previous_dy * previous_dy) ** 0.5
    current_distance = (current_dx * current_dx + current_dy * current_dy) ** 0.5

    translated_pan = (
        pan[0] + current_center[0] - previous_center[0],
        pan[1] + current_center[1] - previous_center[1],
    )
    if previous_distance <= 1e-9:
        return zoom, translated_pan
    return _zoom_about_point(
        zoom=zoom,
        pan=translated_pan,
        anchor=current_center,
        viewport_center=viewport_center,
        requested_zoom=zoom * current_distance / previous_distance,
    )


class EpicycleCanvas(QWidget):
    """Paint-only view of a ready immutable frame; it never calculates Fourier state."""

    view_zoom_changed = Signal(float)

    def __init__(self, translator: Translator, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._translator = translator
        self._frame: EpicycleFrame | None = None
        self._frame_cache_key: tuple[int, int, tuple[int, ...]] | None = None
        self._scene_bounds: tuple[float, float, float, float] | None = None
        self._original_scene_path = QPainterPath()
        self._reconstruction_scene_path = QPainterPath()
        self._vector_lines: list[QLineF] = []
        self._circle_centers: list[tuple[float, float, float]] = []
        self._vector_colors: list[QColor] = []
        self._circle_colors: list[QColor] = []
        self._view_zoom = _VIEW_ZOOM_DEFAULT
        self._view_pan = QPointF()
        self._pan_anchor: QPointF | None = None
        self._touch_points: dict[int, tuple[float, float]] = {}
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

    def set_view_zoom(self, zoom: float) -> None:
        """Set a bounded view scale; rendering remains independent from Fourier state."""

        next_zoom = _bounded_view_zoom(zoom)
        if next_zoom == self._view_zoom:
            return
        self._view_zoom = next_zoom
        self.update()
        self.view_zoom_changed.emit(self._view_zoom)

    def reset_view(self) -> None:
        """Restore the fitted scene scale selected for a new desktop view."""

        zoom_changed = self._view_zoom != _VIEW_ZOOM_DEFAULT
        self._view_zoom = _VIEW_ZOOM_DEFAULT
        self._view_pan = QPointF()
        self._pan_anchor = None
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
            viewport_center=(self.width() / 2.0, self.height() / 2.0),
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
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._pan_anchor is not None and event.buttons() & Qt.MouseButton.LeftButton:
            position = event.position()
            delta = position - self._pan_anchor
            self._view_pan = QPointF(
                self._view_pan.x() + delta.x(), self._view_pan.y() + delta.y()
            )
            self._pan_anchor = position
            self.update()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() is Qt.MouseButton.LeftButton and self._pan_anchor is not None:
            self._pan_anchor = None
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        wheel_delta = event.angleDelta().y()
        if wheel_delta == 0:
            event.ignore()
            return
        zoom_factor = 1.15 ** (wheel_delta / 120.0)
        next_zoom, next_pan = _zoom_about_point(
            zoom=self._view_zoom,
            pan=self.view_pan,
            anchor=(event.position().x(), event.position().y()),
            viewport_center=(self.width() / 2.0, self.height() / 2.0),
            requested_zoom=self._view_zoom * zoom_factor,
        )
        if next_zoom != self._view_zoom:
            self._view_zoom = next_zoom
            self._view_pan = QPointF(*next_pan)
            self.update()
            self.view_zoom_changed.emit(self._view_zoom)
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
        minimum_x, maximum_x, minimum_y, maximum_y = scene_bounds
        span = max(maximum_x - minimum_x, maximum_y - minimum_y, 1.0) * 1.15
        scale = min(self.width(), self.height()) / span * self._view_zoom
        center_x = (minimum_x + maximum_x) / 2.0
        center_y = (minimum_y + maximum_y) / 2.0
        scale = max(scale, 1e-12)
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
            for (x, y, radius), color in zip(
                self._circle_centers, self._circle_colors, strict=True
            ):
                painter.setPen(QPen(color, 1.0 * line_scale))
                painter.drawEllipse(QPointF(x, y), radius, radius)
        if visibility.vectors:
            for line, color in zip(self._vector_lines, self._vector_colors, strict=True):
                painter.setPen(QPen(color, 1.2 * line_scale))
                painter.drawLine(line)
        if visibility.endpoint:
            painter.setBrush(QColor("#dc2626"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(map_point(frame.chain.endpoint), 4.0 * line_scale, 4.0 * line_scale)
        painter.restore()


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
        self._settings = QSettings("fourier-sketch", "desktop")
        self._last_tick = monotonic()
        self._canvas = EpicycleCanvas(self._translator)
        self._pages: QStackedWidget
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
        for key in ("monochrome", "edges", "contours", "curve", "spectrum", "export"):
            button = QPushButton(self._translator.text(f"desktop.page.{key}"))
            button.setEnabled(False)
            button.setToolTip(self._translator.text("desktop.deferred"))
            sidebar.addWidget(button)
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
            toggle.setChecked(True)
            toggle.toggled.connect(
                lambda checked, selected=field: self._set_visibility(selected, checked)
            )
            options.addRow(toggle)
        center.addLayout(options)
        layout.addLayout(center, 2)
        self.setCentralWidget(root)
        self._source.completed.connect(self._build_freehand)
        self._source.changed.connect(self._capture_changed)
        self._set_status(self._translator.text("desktop.status.initial"))

    def _capture_changed(self, snapshot: object) -> None:
        count = len(getattr(snapshot, "points", ()))
        self._set_status(self._translator.text("desktop.status.captured", count=count))

    def _build_freehand(self, snapshot: object) -> None:
        points = tuple(getattr(snapshot, "points", ()))
        if not points:
            return

        def operation() -> EpicycleTimeline:
            curve = Curve(points, closed=False)
            return build_freehand_timeline(curve)

        self._start_job(operation, self._apply_timeline)

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
        self, operation: Callable[[], object], on_success: Callable[[object], None]
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
            job.wait(3000)
            if job.isRunning():
                job.terminate()
                job.wait(3000)
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

    def _apply_timeline(self, timeline: object) -> None:
        if not isinstance(timeline, EpicycleTimeline):
            self._set_status(self._translator.text("desktop.status.runtime"))
            return
        self._timeline = timeline
        speed = self._speed.value() / _SPEED_SCALE
        self._apply_frame(timeline.set_speed(speed))

    def _apply_frame(self, frame: object) -> None:
        if not isinstance(frame, EpicycleFrame):
            self._set_status(self._translator.text("desktop.status.runtime"))
            return
        self._canvas.set_frame(frame)
        self._harmonics.setRange(1, frame.selection.sample_count)
        self._harmonics.setValue(frame.selection.coefficient_count)
        self._set_status(
            self._translator.text(
                "status.summary",
                state=frame.timeline_state,
                time=frame.chain.time,
                harmonics=frame.selection.coefficient_count,
                speed=frame.speed,
            )
        )

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
