"""Matplotlib pointer adapter for the bounded freehand application contract."""

from math import isfinite
from typing import Any

from matplotlib.axes import Axes
from matplotlib.backend_bases import KeyEvent, MouseButton, MouseEvent
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.widgets import Button, Slider

from fourier_sketch.application import (
    DEFAULT_FREEHAND_HARMONICS,
    DEFAULT_FREEHAND_SAMPLES,
    CaptureState,
    EpicycleFrame,
    EpicycleTimeline,
    FreehandCapture,
    FreehandCaptureSnapshot,
    FreehandCurveResult,
    build_freehand_timeline,
)
from fourier_sketch.application.diagnostic_epicycles import (
    MAX_INTERACTIVE_HARMONICS,
    MAX_SPEED,
)
from fourier_sketch.domain import DomainValidationError, Point2D
from fourier_sketch.math import MAX_RESAMPLED_POINTS
from fourier_sketch.presentation import Translator

from .matplotlib_epicycles import draw_frame


class FreehandControlPanel:
    """Persistent Matplotlib controls bound to one freehand surface."""

    def __init__(
        self,
        *,
        play_button: Button,
        pause_button: Button,
        restart_button: Button,
        speed_slider: Slider,
        harmonic_slider: Slider | None,
    ) -> None:
        self.play_button = play_button
        self.pause_button = pause_button
        self.restart_button = restart_button
        self.speed_slider = speed_slider
        self.harmonic_slider = harmonic_slider


class FreehandSurface:
    """Actual canvas callbacks around capture state and the accepted renderer."""

    def __init__(
        self,
        figure: Figure,
        drawing_axes: Axes,
        render_axes: Axes,
        translator: Translator,
        *,
        sample_count: int = DEFAULT_FREEHAND_SAMPLES,
        harmonic_count: int | None = None,
        speed: float = 1.0,
        closed: bool = False,
        capture: FreehandCapture | None = None,
    ) -> None:
        if not isinstance(figure, Figure):
            raise DomainValidationError("figure must be a matplotlib Figure")
        if not isinstance(drawing_axes, Axes) or not isinstance(render_axes, Axes):
            raise DomainValidationError("freehand axes must be matplotlib Axes")
        if drawing_axes is render_axes:
            raise DomainValidationError("drawing and render axes must be distinct")
        if drawing_axes.figure is not figure or render_axes.figure is not figure:
            raise DomainValidationError("freehand axes must belong to figure")
        if not isinstance(translator, Translator):
            raise DomainValidationError("translator must be a Translator")
        (
            validated_sample_count,
            validated_harmonic_count,
            normalized_speed,
            validated_closed,
        ) = _validated_surface_options(sample_count, harmonic_count, speed, closed)

        self.figure = figure
        self.drawing_axes = drawing_axes
        self.render_axes = render_axes
        self._translator = translator
        self._sample_count = validated_sample_count
        self._harmonic_count = validated_harmonic_count
        self._speed = normalized_speed
        self._closed = validated_closed
        if capture is not None and not isinstance(capture, FreehandCapture):
            raise DomainValidationError("capture must be a FreehandCapture")
        self._capture = FreehandCapture() if capture is None else capture
        self._curve_result: FreehandCurveResult | None = None
        self._timeline: EpicycleTimeline | None = None
        self._latest_frame: EpicycleFrame | None = None
        self._controls: FreehandControlPanel | None = None
        self._status_key = "freehand.status.empty"
        self._callback_ids = (
            figure.canvas.mpl_connect("button_press_event", self._on_press),
            figure.canvas.mpl_connect("motion_notify_event", self._on_motion),
            figure.canvas.mpl_connect("button_release_event", self._on_release),
            figure.canvas.mpl_connect("key_press_event", self._on_key),
        )
        self._draw_capture()
        self._draw_empty_render_state()

    @property
    def callback_ids(self) -> tuple[int, ...]:
        return self._callback_ids

    @property
    def has_timeline(self) -> bool:
        return self._timeline is not None

    @property
    def timeline(self) -> EpicycleTimeline:
        if self._timeline is None:
            raise DomainValidationError("freehand timeline is not available")
        return self._timeline

    @property
    def curve_result(self) -> FreehandCurveResult:
        if self._curve_result is None:
            raise DomainValidationError("freehand curve result is not available")
        return self._curve_result

    @property
    def latest_frame(self) -> EpicycleFrame:
        if self._latest_frame is None:
            raise DomainValidationError("freehand frame is not available")
        return self._latest_frame

    @property
    def controls(self) -> FreehandControlPanel:
        if self._controls is None:
            raise DomainValidationError("freehand controls are not attached")
        return self._controls

    def capture_snapshot(self) -> FreehandCaptureSnapshot:
        return self._capture.snapshot()

    def reset(self) -> FreehandCaptureSnapshot:
        snapshot = self._capture.reset()
        self._curve_result = None
        self._timeline = None
        self._latest_frame = None
        self._status_key = "freehand.status.empty"
        self._draw_capture()
        self._draw_empty_render_state()
        return snapshot

    def cancel(self) -> FreehandCaptureSnapshot:
        snapshot = self._capture.cancel()
        self._curve_result = None
        self._timeline = None
        self._latest_frame = None
        self._status_key = "freehand.status.cancelled"
        self._draw_capture()
        self._draw_empty_render_state()
        return snapshot

    def tick(self, delta_seconds: float) -> EpicycleFrame:
        frame = self.timeline.advance(delta_seconds)
        return self._show_frame(frame)

    def play(self) -> EpicycleFrame | None:
        """Start the captured stroke timeline without creating an alternate path."""
        if self._timeline is None:
            self._show_missing_timeline()
            return None
        return self._show_frame(self._timeline.play())

    def pause(self) -> EpicycleFrame | None:
        """Pause the captured stroke timeline."""
        if self._timeline is None:
            self._show_missing_timeline()
            return None
        return self._show_frame(self._timeline.pause())

    def restart(self) -> EpicycleFrame | None:
        """Restart the current timeline while preserving the accepted source stroke."""
        if self._timeline is None:
            self._show_missing_timeline()
            return None
        return self._show_frame(self._timeline.restart())

    def set_speed(self, speed: float) -> EpicycleFrame | None:
        """Apply a validated speed to the current or next stroke timeline."""
        normalized = _validated_surface_options(
            self._sample_count,
            self._harmonic_count,
            speed,
            self._closed,
        )[2]
        self._speed = normalized
        if self._timeline is None:
            return None
        return self._show_frame(self._timeline.set_speed(normalized))

    def set_harmonic_count(self, harmonic_count: int) -> EpicycleFrame | None:
        """Apply an explicit harmonic count without weakening timeline validation."""
        validated = _validated_surface_options(
            self._sample_count,
            harmonic_count,
            self._speed,
            self._closed,
        )[1]
        if self._timeline is None:
            self._harmonic_count = validated
            return None
        frame = self._timeline.set_harmonic_count(validated)
        self._harmonic_count = validated
        return self._show_frame(frame)

    def attach_controls(self) -> FreehandControlPanel:
        """Attach one reusable control set to this surface."""
        if self._controls is not None:
            return self._controls
        play_button = Button(
            self.figure.add_axes((0.08, 0.12, 0.10, 0.055)),
            self._translator.text("control.play"),
        )
        pause_button = Button(
            self.figure.add_axes((0.20, 0.12, 0.10, 0.055)),
            self._translator.text("control.pause"),
        )
        restart_button = Button(
            self.figure.add_axes((0.32, 0.12, 0.10, 0.055)),
            self._translator.text("control.restart"),
        )
        speed_slider = Slider(
            self.figure.add_axes((0.52, 0.14, 0.38, 0.035)),
            self._translator.text("control.speed"),
            min(0.1, self._speed),
            MAX_SPEED,
            valinit=self._speed,
        )
        harmonic_slider: Slider | None = None
        if self._sample_count > 1:
            harmonic_slider = Slider(
                self.figure.add_axes((0.52, 0.07, 0.38, 0.035)),
                self._translator.text("control.harmonics"),
                1,
                self._sample_count,
                valinit=self._harmonic_count,
                valstep=1,
            )

        play_button.on_clicked(lambda _event: self.play())
        pause_button.on_clicked(lambda _event: self.pause())
        restart_button.on_clicked(lambda _event: self.restart())
        speed_slider.on_changed(lambda value: self.set_speed(float(value)))
        if harmonic_slider is not None:
            harmonic_slider.on_changed(self._on_harmonic_control)
        self._controls = FreehandControlPanel(
            play_button=play_button,
            pause_button=pause_button,
            restart_button=restart_button,
            speed_slider=speed_slider,
            harmonic_slider=harmonic_slider,
        )
        return self._controls

    def disconnect(self) -> None:
        for callback_id in self._callback_ids:
            self.figure.canvas.mpl_disconnect(callback_id)

    def _on_press(self, event: MouseEvent) -> None:
        if event.button is not MouseButton.LEFT:
            return
        point = self._event_point(event)
        if point is None:
            return
        self._capture.pointer_down(point)
        self._curve_result = None
        self._timeline = None
        self._latest_frame = None
        self._status_key = "freehand.status.capturing"
        self._draw_capture()
        self._draw_empty_render_state()

    def _on_motion(self, event: MouseEvent) -> None:
        if self._capture.snapshot().state is not CaptureState.CAPTURING:
            return
        point = self._event_point(event)
        if point is None:
            return
        snapshot = self._capture.pointer_move(point)
        self._status_key = (
            "freehand.status.limit"
            if snapshot.state is CaptureState.LIMIT_REACHED
            else "freehand.status.capturing"
        )
        self._draw_capture()

    def _on_release(self, event: MouseEvent) -> None:
        if event.button is not MouseButton.LEFT:
            return
        if self._capture.snapshot().state is CaptureState.CAPTURING:
            release_point = self._event_point(event)
            if release_point is not None:
                self._capture.pointer_move(release_point)
        snapshot = self._capture.pointer_up()
        if snapshot.state is CaptureState.LIMIT_REACHED:
            self._status_key = "freehand.status.limit"
            self._draw_capture()
            return
        if snapshot.state is not CaptureState.READY:
            return
        try:
            result = self._capture.build_curve(
                sample_count=self._sample_count,
                closed=self._closed,
            )
            timeline = build_freehand_timeline(
                result.sampled_curve,
                harmonic_count=min(
                    self._harmonic_count,
                    result.sampled_curve.sample_count,
                ),
                speed=self._speed,
            )
            frame = timeline.play()
        except DomainValidationError:
            self._status_key = "freehand.status.invalid"
            self._draw_capture()
            return
        self._curve_result = result
        self._timeline = timeline
        self._latest_frame = frame
        self._synchronize_controls(timeline)
        self._status_key = "freehand.status.ready"
        self._draw_capture()
        draw_frame(self.render_axes, frame, self._translator)
        self.figure.canvas.draw_idle()

    def _on_key(self, event: KeyEvent) -> None:
        if event.key == "escape":
            self.cancel()
        elif event.key == "r":
            self.reset()

    def _event_point(self, event: MouseEvent) -> Point2D | None:
        if event.inaxes is not self.drawing_axes or event.xdata is None or event.ydata is None:
            return None
        try:
            return Point2D(event.xdata, event.ydata)
        except DomainValidationError:
            self._status_key = "freehand.status.invalid"
            self._draw_capture()
            return None

    def _draw_capture(self) -> None:
        snapshot = self._capture.snapshot()
        self.drawing_axes.clear()
        if snapshot.points:
            self.drawing_axes.plot(
                tuple(point.x for point in snapshot.points),
                tuple(point.y for point in snapshot.points),
                color="#e76f51",
                linewidth=2.0,
                marker="o" if len(snapshot.points) == 1 else None,
            )
        self.drawing_axes.set_title(self._translator.text("freehand.input.title"))
        self.drawing_axes.set_xlabel(self._translator.text("axis.x"))
        self.drawing_axes.set_ylabel(self._translator.text("axis.y"))
        self.drawing_axes.text(
            0.01,
            0.99,
            self._translator.text(self._status_key, count=len(snapshot.points)),
            transform=self.drawing_axes.transAxes,
            ha="left",
            va="top",
            fontsize=9,
        )
        self.drawing_axes.text(
            0.01,
            0.01,
            self._translator.text("freehand.instructions"),
            transform=self.drawing_axes.transAxes,
            ha="left",
            va="bottom",
            fontsize=8,
        )
        self.drawing_axes.grid(True, linewidth=0.4, alpha=0.3)
        self.drawing_axes.set_aspect("equal", adjustable="box")
        self.drawing_axes.set_xlim(-1.1, 1.1)
        self.drawing_axes.set_ylim(-1.1, 1.1)
        self.figure.canvas.draw_idle()

    def _draw_empty_render_state(self) -> None:
        self.render_axes.clear()
        self.render_axes.set_title(self._translator.text("freehand.output.title"))
        self.render_axes.text(
            0.5,
            0.5,
            self._translator.text("freehand.output.empty"),
            transform=self.render_axes.transAxes,
            ha="center",
            va="center",
        )
        self.render_axes.set_axis_off()
        self.figure.canvas.draw_idle()

    def _show_frame(self, frame: EpicycleFrame) -> EpicycleFrame:
        self._latest_frame = frame
        draw_frame(self.render_axes, frame, self._translator)
        self.figure.canvas.draw_idle()
        return frame

    def _show_missing_timeline(self) -> None:
        self._draw_empty_render_state()
        return None

    def _on_harmonic_control(self, value: float) -> None:
        try:
            self.set_harmonic_count(int(value))
        except DomainValidationError:
            if self._controls is not None and self._controls.harmonic_slider is not None:
                slider = self._controls.harmonic_slider
                eventson = slider.eventson
                slider.eventson = False
                slider.set_val(self.timeline.harmonic_count)
                slider.eventson = eventson
            self._status_key = "freehand.status.invalid"
            self._draw_capture()

    def _synchronize_controls(self, timeline: EpicycleTimeline) -> None:
        if self._controls is None:
            return
        speed_slider = self._controls.speed_slider
        speed_eventson = speed_slider.eventson
        speed_slider.eventson = False
        speed_slider.set_val(timeline.speed)
        speed_slider.eventson = speed_eventson

        harmonic_slider = self._controls.harmonic_slider
        if harmonic_slider is None:
            return
        harmonic_eventson = harmonic_slider.eventson
        harmonic_slider.eventson = False
        harmonic_slider.set_val(timeline.harmonic_count)
        harmonic_slider.eventson = harmonic_eventson
        harmonic_slider.set_active(timeline.maximum_harmonics > 1)


def create_freehand_surface(
    translator: Translator,
    *,
    sample_count: int = DEFAULT_FREEHAND_SAMPLES,
    harmonic_count: int | None = None,
    speed: float = 1.0,
    closed: bool = False,
    capture: FreehandCapture | None = None,
) -> FreehandSurface:
    """Create an Agg-backed surface suitable for component and live headless tests."""
    if not isinstance(translator, Translator):
        raise DomainValidationError("translator must be a Translator")
    validated = _validated_surface_options(sample_count, harmonic_count, speed, closed)
    figure = Figure(figsize=(12.0, 6.0))
    FigureCanvasAgg(figure)
    drawing_axes, render_axes = figure.subplots(1, 2)
    figure.subplots_adjust(wspace=0.25, bottom=0.27)
    surface = FreehandSurface(
        figure,
        drawing_axes,
        render_axes,
        translator,
        sample_count=validated[0],
        harmonic_count=validated[1],
        speed=validated[2],
        closed=validated[3],
        capture=capture,
    )
    surface.attach_controls()
    return surface


def run_freehand_interactive(
    translator: Translator,
    *,
    sample_count: int = DEFAULT_FREEHAND_SAMPLES,
    harmonic_count: int | None = None,
    speed: float = 1.0,
    closed: bool = False,
    interval_ms: int = 33,
) -> None:
    """Open the fully working temporary freehand diagnostic window."""
    if not isinstance(translator, Translator):
        raise DomainValidationError("translator must be a Translator")
    if isinstance(interval_ms, bool) or not isinstance(interval_ms, int) or interval_ms < 10:
        raise DomainValidationError("interval_ms must be an integer of at least 10")
    validated = _validated_surface_options(sample_count, harmonic_count, speed, closed)

    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation

    figure, axes = plt.subplots(1, 2, figsize=(12.0, 6.0))
    figure.subplots_adjust(wspace=0.25, bottom=0.27)
    surface = FreehandSurface(
        figure,
        axes[0],
        axes[1],
        translator,
        sample_count=validated[0],
        harmonic_count=validated[1],
        speed=validated[2],
        closed=validated[3],
    )
    surface.attach_controls()

    def animate(_frame_index: int) -> tuple[Any, ...]:
        if surface.has_timeline:
            surface.tick(interval_ms / 1000.0)
        return ()

    animation = FuncAnimation(
        figure,
        animate,
        interval=interval_ms,
        cache_frame_data=False,
    )
    _ = animation
    plt.show()


def _validated_surface_options(
    sample_count: int,
    harmonic_count: int | None,
    speed: float,
    closed: bool,
) -> tuple[int, int, float, bool]:
    if isinstance(sample_count, bool) or not isinstance(sample_count, int):
        raise DomainValidationError("sample_count must be an integer")
    if sample_count < 1 or sample_count > MAX_RESAMPLED_POINTS:
        raise DomainValidationError(f"sample_count must be between 1 and {MAX_RESAMPLED_POINTS}")
    validated_harmonic_count = min(DEFAULT_FREEHAND_HARMONICS, sample_count)
    if harmonic_count is not None:
        if isinstance(harmonic_count, bool) or not isinstance(harmonic_count, int):
            raise DomainValidationError("harmonic_count must be an integer")
        validated_harmonic_count = harmonic_count
    if validated_harmonic_count < 1 or validated_harmonic_count > min(
        sample_count,
        MAX_INTERACTIVE_HARMONICS,
    ):
        raise DomainValidationError("harmonic_count is outside the freehand sample budget")
    if isinstance(speed, bool) or not isinstance(speed, (int, float)):
        raise DomainValidationError(f"speed must be greater than zero and at most {MAX_SPEED}")
    try:
        normalized_speed = float(speed)
    except OverflowError as error:
        raise DomainValidationError("speed must be finite") from error
    if not isfinite(normalized_speed) or normalized_speed <= 0.0 or normalized_speed > MAX_SPEED:
        raise DomainValidationError(f"speed must be greater than zero and at most {MAX_SPEED}")
    if not isinstance(closed, bool):
        raise DomainValidationError("closed must be a boolean")
    return sample_count, validated_harmonic_count, normalized_speed, closed
