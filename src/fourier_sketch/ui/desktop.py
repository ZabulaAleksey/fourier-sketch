"""Responsive PySide6 shell that only dispatches existing application use cases."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from time import monotonic

from PySide6.QtCore import QPointF, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QCloseEvent, QColor, QMouseEvent, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
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
    build_freehand_timeline,
)
from fourier_sketch.domain import Curve, DomainValidationError, Point2D
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
            self.finished_snapshot.emit(self._operation())
        except Exception:
            self.failed.emit("desktop.error.runtime")


class EpicycleCanvas(QWidget):
    """Paint-only view of a ready immutable frame; it never calculates Fourier state."""

    def __init__(self, translator: Translator, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._translator = translator
        self._frame: EpicycleFrame | None = None
        self.setMinimumSize(360, 300)
        self.setAccessibleName("Epicycles canvas")

    def set_frame(self, frame: EpicycleFrame | None) -> None:
        self._frame = frame
        self.update()

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
        points = [*frame.original.points, *frame.reconstruction.points, *frame.trace]
        for vector in frame.chain.vectors:
            points.extend((vector.start, vector.end))
        minimum_x = min(point.x for point in points)
        maximum_x = max(point.x for point in points)
        minimum_y = min(point.y for point in points)
        maximum_y = max(point.y for point in points)
        span = max(maximum_x - minimum_x, maximum_y - minimum_y, 1.0) * 1.15
        scale = min(self.width(), self.height()) / span
        center_x = (minimum_x + maximum_x) / 2.0
        center_y = (minimum_y + maximum_y) / 2.0

        def map_point(point: Point2D) -> QPointF:
            return QPointF(
                self.width() / 2.0 + (point.x - center_x) * scale,
                self.height() / 2.0 - (point.y - center_y) * scale,
            )

        def draw_polyline(points_to_draw: tuple[Point2D, ...], color: str, width: float) -> None:
            if len(points_to_draw) < 2:
                return
            path = QPainterPath(map_point(points_to_draw[0]))
            for point in points_to_draw[1:]:
                path.lineTo(map_point(point))
            painter.setPen(QPen(QColor(color), width))
            painter.drawPath(path)

        visibility = frame.visibility
        if visibility.original:
            draw_polyline(
                frame.original.points + ((frame.original.start,) if frame.original.closed else ()),
                "#94a3b8",
                1.0,
            )
        if visibility.reconstruction:
            draw_polyline(
                frame.reconstruction.points
                + ((frame.reconstruction.start,) if frame.reconstruction.closed else ()),
                "#14b8a6",
                1.4,
            )
        if visibility.trace:
            draw_polyline(frame.trace, "#ef4444", 2.0)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        if visibility.circles:
            painter.setPen(QPen(QColor("#3b82f6"), 1.0))
            for vector in frame.chain.vectors:
                center = map_point(vector.start)
                radius = vector.amplitude * scale
                painter.drawEllipse(center, radius, radius)
        if visibility.vectors:
            painter.setPen(QPen(QColor("#1e3a8a"), 1.2))
            for vector in frame.chain.vectors:
                painter.drawLine(map_point(vector.start), map_point(vector.end))
        if visibility.endpoint:
            painter.setBrush(QColor("#dc2626"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(map_point(frame.chain.endpoint), 4.0, 4.0)


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
        path = QPainterPath(QPointF(points[0].x, points[0].y))
        for point in points[1:]:
            path.lineTo(point.x, point.y)
        painter.setPen(QPen(QColor("#1d4ed8"), 2.0))
        painter.drawPath(path)

    def _point(self, position: QPointF) -> Point2D:
        return Point2D(float(position.x()), float(position.y()))


class DesktopWindow(QMainWindow):
    """Desktop workflow with bounded worker shutdown and explicit UI states."""

    def __init__(self, *, locale: str | None = None) -> None:
        super().__init__()
        self._translator = Translator(resolve_locale(locale))
        self._image = ImageMvpController()
        self._timeline: EpicycleTimeline | None = None
        self._job: _Job | None = None
        self._last_tick = monotonic()
        self._canvas = EpicycleCanvas(self._translator)
        self._pages: QStackedWidget
        self._status = QLabel()
        self._source = FreehandCanvas()
        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._tick)
        self._build()
        self._timer.start()

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
        source_layout.addWidget(QLabel(self._translator.text("desktop.source.instructions")))
        source_layout.addWidget(self._source)
        buttons = QHBoxLayout()
        clear = QPushButton(self._translator.text("desktop.source.clear"))
        clear.clicked.connect(self._source.reset)
        image = QPushButton(self._translator.text("desktop.source.choose_image"))
        image.clicked.connect(self._choose_image)
        buttons.addWidget(clear)
        buttons.addWidget(image)
        source_layout.addLayout(buttons)
        self._pages.addWidget(source_page)
        layout.addWidget(self._pages, 1)
        center = QVBoxLayout()
        center.addWidget(self._canvas, 1)
        center.addWidget(self._status)
        controls = QHBoxLayout()
        self._play = QPushButton(self._translator.text("control.play"))
        self._pause = QPushButton(self._translator.text("control.pause"))
        restart = QPushButton(self._translator.text("control.restart"))
        cancel = QPushButton(self._translator.text("desktop.control.cancel"))
        self._play.clicked.connect(lambda: self._timeline_action("play"))
        self._pause.clicked.connect(lambda: self._timeline_action("pause"))
        restart.clicked.connect(lambda: self._timeline_action("restart"))
        cancel.clicked.connect(self._cancel_current_job)
        controls.addWidget(self._play)
        controls.addWidget(self._pause)
        controls.addWidget(restart)
        controls.addWidget(cancel)
        center.addLayout(controls)
        options = QFormLayout()
        self._harmonics = QSlider(Qt.Orientation.Horizontal)
        self._speed = QSlider(Qt.Orientation.Horizontal)
        self._speed.setRange(1, 100)
        self._speed.setValue(10)
        self._harmonics.valueChanged.connect(
            lambda value: self._timeline_action("harmonics", value)
        )
        self._speed.valueChanged.connect(lambda value: self._timeline_action("speed", value / 10.0))
        options.addRow(self._translator.text("control.harmonics"), self._harmonics)
        options.addRow(self._translator.text("control.speed"), self._speed)
        for field in ("circles", "vectors", "endpoint", "trace", "original", "reconstruction"):
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
        generation = self._image.begin(ImageMvpConfig())
        self._set_status(self._translator.text("desktop.status.processing"))
        self._start_job(lambda: self._image.process(generation, Path(name)), self._apply_image)

    def _start_job(
        self, operation: Callable[[], object], on_success: Callable[[object], None]
    ) -> None:
        if self._job is not None and self._job.isRunning():
            self._set_status(self._translator.text("desktop.status.busy"))
            return
        self._job = _Job(operation)
        self._job.finished_snapshot.connect(on_success)
        self._job.failed.connect(
            lambda _key: self._set_status(self._translator.text("desktop.status.runtime"))
        )
        self._job.finished.connect(self._job_finished)
        self._job.start()

    def _cancel_current_job(self) -> None:
        self._image.cancel()
        if self._job is not None and self._job.isRunning():
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
        self._apply_frame(timeline.snapshot())

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
        now = monotonic()
        delta = now - self._last_tick
        self._last_tick = now
        self._timeline_action("advance", delta)

    def closeEvent(self, event: QCloseEvent) -> None:
        self._timer.stop()
        self._image.cancel()
        if self._job is not None and self._job.isRunning():
            self._job.wait(3000)
        event.accept()

    def _set_status(self, text: str) -> None:
        self._status.setText(text)


def run_desktop(*, locale: str | None = None) -> int:
    app = QApplication.instance() or QApplication([])
    window = DesktopWindow(locale=locale)
    window.resize(1200, 760)
    window.show()
    return app.exec()
