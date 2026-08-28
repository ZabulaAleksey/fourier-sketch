"""Matplotlib four-panel surface for the FS-013 image MVP."""

import os
import tempfile
from concurrent.futures import CancelledError, Future, ThreadPoolExecutor
from contextlib import suppress
from pathlib import Path
from typing import Any, cast

import numpy as np
from matplotlib.axes import Axes
from matplotlib.backend_bases import KeyEvent
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.widgets import Button, CheckButtons, RadioButtons, Slider

from fourier_sketch.application import (
    ImageContourTimelineResult,
    ImageMvpConfig,
    ImageMvpController,
    ImageMvpSnapshot,
    ImageMvpState,
    ImageNoContourResult,
    TimelineState,
    validate_local_path,
)
from fourier_sketch.application.diagnostic_epicycles import MAX_SPEED
from fourier_sketch.domain import DomainValidationError
from fourier_sketch.imaging import (
    DenoiseMode,
    EdgeAlgorithm,
    ImagePreprocessingOptions,
    RasterImage,
)
from fourier_sketch.presentation import Translator

from .matplotlib_epicycles import draw_frame


class ImageMvpControlPanel:
    """Persistent controls whose callbacks dispatch application commands only."""

    def __init__(
        self,
        *,
        process_button: Button,
        cancel_button: Button,
        play_button: Button,
        pause_button: Button,
        restart_button: Button,
        threshold_slider: Slider,
        sample_slider: Slider,
        harmonic_slider: Slider,
        speed_slider: Slider,
        algorithm_buttons: RadioButtons,
        preprocessing_checks: CheckButtons,
    ) -> None:
        self.process_button = process_button
        self.cancel_button = cancel_button
        self.play_button = play_button
        self.pause_button = pause_button
        self.restart_button = restart_button
        self.threshold_slider = threshold_slider
        self.sample_slider = sample_slider
        self.harmonic_slider = harmonic_slider
        self.speed_slider = speed_slider
        self.algorithm_buttons = algorithm_buttons
        self.preprocessing_checks = preprocessing_checks


class ImageMvpSurface:
    """One selectable-image workflow with bounded background processing."""

    def __init__(
        self,
        figure: Figure,
        axes: tuple[Axes, Axes, Axes, Axes],
        input_path: Path,
        translator: Translator,
        *,
        config: ImageMvpConfig | None = None,
        controller: ImageMvpController | None = None,
    ) -> None:
        if not isinstance(figure, Figure):
            raise DomainValidationError("image MVP figure must be a matplotlib Figure")
        if (
            not isinstance(axes, tuple)
            or len(axes) != 4
            or any(not isinstance(item, Axes) or item.figure is not figure for item in axes)
        ):
            raise DomainValidationError("image MVP requires four axes from the same figure")
        if not isinstance(input_path, Path):
            raise DomainValidationError("image MVP input must be a pathlib.Path")
        if not isinstance(translator, Translator):
            raise DomainValidationError("image MVP translator must be a Translator")
        if config is not None and not isinstance(config, ImageMvpConfig):
            raise DomainValidationError("image MVP config must be typed")
        if controller is not None and not isinstance(controller, ImageMvpController):
            raise DomainValidationError("image MVP controller must be typed")

        self.figure = figure
        self.grayscale_axes, self.binary_axes, self.contour_axes, self.epicycle_axes = axes
        self.input_path = validate_local_path(input_path, field_name="input")
        self._translator = translator
        self._initial_config = config or ImageMvpConfig()
        self._controller = controller or ImageMvpController()
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="image-mvp")
        self._future: Future[ImageMvpSnapshot] | None = None
        self._controls: ImageMvpControlPanel | None = None
        self._closed = False
        self._limitations_artist: Any | None = None
        self._algorithm_labels = {
            translator.text(f"image_mvp.algorithm.{algorithm.value}"): algorithm
            for algorithm in EdgeAlgorithm
        }
        self._key_callback = figure.canvas.mpl_connect("key_press_event", self._on_key)
        self._draw(self._controller.snapshot())

    @property
    def controls(self) -> ImageMvpControlPanel:
        if self._controls is None:
            raise DomainValidationError("image MVP controls are not attached")
        return self._controls

    @property
    def snapshot(self) -> ImageMvpSnapshot:
        return self._controller.snapshot()

    def attach_controls(self) -> ImageMvpControlPanel:
        if self._controls is not None:
            return self._controls
        config = self._initial_config
        process_button = Button(
            self.figure.add_axes((0.04, 0.205, 0.10, 0.045)),
            self._translator.text("image_mvp.control.process"),
        )
        cancel_button = Button(
            self.figure.add_axes((0.15, 0.205, 0.10, 0.045)),
            self._translator.text("image_mvp.control.cancel"),
        )
        play_button = Button(
            self.figure.add_axes((0.27, 0.205, 0.08, 0.045)),
            self._translator.text("control.play"),
        )
        pause_button = Button(
            self.figure.add_axes((0.36, 0.205, 0.08, 0.045)),
            self._translator.text("control.pause"),
        )
        restart_button = Button(
            self.figure.add_axes((0.45, 0.205, 0.09, 0.045)),
            self._translator.text("control.restart"),
        )
        threshold_slider = Slider(
            self.figure.add_axes((0.64, 0.215, 0.30, 0.025)),
            self._translator.text("image_mvp.control.threshold"),
            0,
            255,
            valinit=config.preprocessing.threshold,
            valstep=1,
        )
        sample_slider = Slider(
            self.figure.add_axes((0.64, 0.165, 0.30, 0.025)),
            self._translator.text("image_mvp.control.samples"),
            3,
            4096,
            valinit=config.sample_count,
            valstep=1,
        )
        harmonic_slider = Slider(
            self.figure.add_axes((0.64, 0.115, 0.30, 0.025)),
            self._translator.text("control.harmonics"),
            1,
            4096,
            valinit=config.harmonic_count,
            valstep=1,
        )
        speed_slider = Slider(
            self.figure.add_axes((0.64, 0.065, 0.30, 0.025)),
            self._translator.text("control.speed"),
            min(0.1, config.speed),
            MAX_SPEED,
            valinit=config.speed,
        )
        algorithm_labels = tuple(self._algorithm_labels)
        algorithm_buttons = RadioButtons(
            self.figure.add_axes((0.04, 0.04, 0.25, 0.13)),
            algorithm_labels,
            active=tuple(EdgeAlgorithm).index(config.algorithm),
        )
        preprocessing_labels = (
            self._translator.text("image_mvp.option.median"),
            self._translator.text("image_mvp.option.autocontrast"),
            self._translator.text("image_mvp.option.invert"),
        )
        preprocessing_checks = CheckButtons(
            self.figure.add_axes((0.32, 0.04, 0.24, 0.13)),
            preprocessing_labels,
            (
                config.preprocessing.denoise is DenoiseMode.MEDIAN_3,
                config.preprocessing.autocontrast,
                config.preprocessing.invert,
            ),
        )

        process_button.on_clicked(lambda _event: self.start())
        cancel_button.on_clicked(lambda _event: self.cancel())
        play_button.on_clicked(lambda _event: self.play())
        pause_button.on_clicked(lambda _event: self.pause())
        restart_button.on_clicked(lambda _event: self.restart())
        harmonic_slider.on_changed(self._on_harmonic_change)
        speed_slider.on_changed(self._on_speed_change)

        self._controls = ImageMvpControlPanel(
            process_button=process_button,
            cancel_button=cancel_button,
            play_button=play_button,
            pause_button=pause_button,
            restart_button=restart_button,
            threshold_slider=threshold_slider,
            sample_slider=sample_slider,
            harmonic_slider=harmonic_slider,
            speed_slider=speed_slider,
            algorithm_buttons=algorithm_buttons,
            preprocessing_checks=preprocessing_checks,
        )
        self._synchronize_controls(self.snapshot.state)
        return self._controls

    def start(self, config: ImageMvpConfig | None = None) -> ImageMvpSnapshot:
        if self._closed:
            raise DomainValidationError("image MVP surface is closed")
        if self.snapshot.state is ImageMvpState.PROCESSING:
            return self.snapshot
        selected = self._config_from_controls() if config is None else config
        generation = self._controller.begin(selected)
        processing = self._controller.snapshot()
        self._draw(processing)
        self._future = self._executor.submit(
            self._controller.process,
            generation,
            self.input_path,
        )
        return processing

    def poll(self) -> ImageMvpSnapshot:
        if self._future is not None and self._future.done():
            with suppress(CancelledError):
                self._future.result()
            self._future = None
        snapshot = self._controller.snapshot()
        self._draw(snapshot)
        return snapshot

    def wait_for_completion(self, timeout: float = 10.0) -> ImageMvpSnapshot:
        future = self._future
        if future is not None:
            with suppress(CancelledError):
                future.result(timeout=timeout)
        return self.poll()

    def cancel(self) -> ImageMvpSnapshot:
        snapshot = self._controller.cancel()
        if self._future is not None:
            self._future.cancel()
        self._draw(snapshot)
        return snapshot

    def play(self) -> ImageMvpSnapshot:
        snapshot = self._controller.play()
        self._draw(snapshot)
        return snapshot

    def pause(self) -> ImageMvpSnapshot:
        snapshot = self._controller.pause()
        self._draw(snapshot)
        return snapshot

    def restart(self) -> ImageMvpSnapshot:
        snapshot = self._controller.restart()
        self._draw(snapshot)
        return snapshot

    def tick(self, delta_seconds: float) -> ImageMvpSnapshot:
        snapshot = self._controller.tick(delta_seconds)
        self._draw(snapshot)
        return snapshot

    def close(self) -> None:
        if self._closed:
            return
        self.cancel()
        self.figure.canvas.mpl_disconnect(self._key_callback)
        self._executor.shutdown(wait=False, cancel_futures=True)
        self._closed = True

    def _config_from_controls(self) -> ImageMvpConfig:
        if self._controls is None:
            return self._initial_config
        checks = self._controls.preprocessing_checks.get_status()
        sample_count = int(self._controls.sample_slider.val)
        harmonic_count = min(int(self._controls.harmonic_slider.val), sample_count)
        if harmonic_count != int(self._controls.harmonic_slider.val):
            self._set_slider_without_event(self._controls.harmonic_slider, harmonic_count)
        selected_algorithm = self._controls.algorithm_buttons.value_selected
        return ImageMvpConfig(
            preprocessing=ImagePreprocessingOptions(
                denoise=DenoiseMode.MEDIAN_3 if checks[0] else DenoiseMode.NONE,
                autocontrast=bool(checks[1]),
                threshold=int(self._controls.threshold_slider.val),
                invert=bool(checks[2]),
            ),
            algorithm=self._algorithm_labels[str(selected_algorithm)],
            boundary_parameters=self._initial_config.boundary_parameters,
            canny_parameters=self._initial_config.canny_parameters,
            sample_count=sample_count,
            harmonic_count=harmonic_count,
            speed=float(self._controls.speed_slider.val),
        )

    def _on_harmonic_change(self, value: float) -> None:
        if self.snapshot.state is not ImageMvpState.READY:
            return
        maximum = self.snapshot.config.sample_count
        selected = min(int(value), maximum)
        snapshot = self._controller.set_harmonic_count(selected)
        if selected != int(value) and self._controls is not None:
            self._set_slider_without_event(self._controls.harmonic_slider, selected)
        self._draw(snapshot)

    def _on_speed_change(self, value: float) -> None:
        if self.snapshot.state is ImageMvpState.READY:
            self._draw(self._controller.set_speed(float(value)))

    def _on_key(self, event: KeyEvent) -> None:
        if event.key == "escape":
            self.cancel()
        elif event.key == "enter":
            self.start()
        elif event.key == " " and self.snapshot.state is ImageMvpState.READY:
            assert self.snapshot.frame is not None
            if self.snapshot.frame.timeline_state is TimelineState.RUNNING:
                self.pause()
            else:
                self.play()

    def _draw(self, snapshot: ImageMvpSnapshot) -> None:
        for axes in (
            self.grayscale_axes,
            self.binary_axes,
            self.contour_axes,
            self.epicycle_axes,
        ):
            axes.clear()
        if isinstance(snapshot.result, (ImageContourTimelineResult, ImageNoContourResult)):
            _draw_raster(
                self.grayscale_axes,
                snapshot.result.preprocessing.grayscale,
                self._translator.text("image_mvp.panel.grayscale"),
            )
            _draw_raster(
                self.binary_axes,
                snapshot.result.preprocessing.binary,
                self._translator.text("image_mvp.panel.binary"),
            )
            _draw_raster(
                self.contour_axes,
                snapshot.result.edges.edges,
                self._translator.text("image_mvp.panel.contour"),
            )
            if isinstance(snapshot.result, ImageContourTimelineResult):
                candidate = snapshot.result.selection.candidate
                closed_points = (*candidate.points, candidate.points[0])
                self.contour_axes.plot(
                    tuple(point.column for point in closed_points),
                    tuple(point.row for point in closed_points),
                    color="#e76f51",
                    linewidth=1.5,
                )
                assert snapshot.frame is not None
                draw_frame(self.epicycle_axes, snapshot.frame, self._translator)
                self.epicycle_axes.set_title(
                    self._translator.text("image_mvp.panel.epicycles")
                )
            else:
                self._draw_message(
                    self.epicycle_axes,
                    "image_mvp.panel.epicycles",
                    "image_mvp.status.empty",
                )
        else:
            status_key = f"image_mvp.status.{snapshot.state.value}"
            if snapshot.state is ImageMvpState.ERROR:
                assert snapshot.failure_key is not None
                status_key = snapshot.failure_key
            panel_keys = (
                "image_mvp.panel.grayscale",
                "image_mvp.panel.binary",
                "image_mvp.panel.contour",
                "image_mvp.panel.epicycles",
            )
            for axes, panel_key in zip(
                (
                    self.grayscale_axes,
                    self.binary_axes,
                    self.contour_axes,
                    self.epicycle_axes,
                ),
                panel_keys,
                strict=True,
            ):
                self._draw_message(axes, panel_key, status_key)

        self.figure.suptitle(
            self._translator.text(
                "image_mvp.title",
                state=self._translator.text(f"image_mvp.state.{snapshot.state.value}"),
            )
        )
        limitations = self._translator.text("image_mvp.limitations")
        if self._limitations_artist is None:
            self._limitations_artist = self.figure.text(
                0.5,
                0.01,
                limitations,
                ha="center",
                va="bottom",
                fontsize=8,
            )
        else:
            self._limitations_artist.set_text(limitations)
        self._synchronize_controls(snapshot.state)
        self.figure.canvas.draw_idle()

    def _draw_message(self, axes: Axes, title_key: str, message_key: str) -> None:
        axes.set_title(self._translator.text(title_key))
        axes.text(
            0.5,
            0.5,
            self._translator.text(message_key),
            transform=axes.transAxes,
            ha="center",
            va="center",
            wrap=True,
        )
        axes.set_axis_off()

    def _synchronize_controls(self, state: ImageMvpState) -> None:
        if self._controls is None:
            return
        processing = state is ImageMvpState.PROCESSING
        ready = state is ImageMvpState.READY
        self._controls.process_button.set_active(not processing)
        self._controls.cancel_button.set_active(processing)
        self._controls.play_button.set_active(ready)
        self._controls.pause_button.set_active(ready)
        self._controls.restart_button.set_active(ready)
        self._controls.threshold_slider.set_active(not processing)
        self._controls.sample_slider.set_active(not processing)
        self._controls.harmonic_slider.set_active(not processing)
        self._controls.speed_slider.set_active(not processing)
        self._controls.algorithm_buttons.active = not processing
        self._controls.preprocessing_checks.active = not processing

    @staticmethod
    def _set_slider_without_event(slider: Slider, value: int) -> None:
        eventson = slider.eventson
        slider.eventson = False
        slider.set_val(value)
        slider.eventson = eventson


def create_image_mvp_surface(
    input_path: Path,
    translator: Translator,
    *,
    config: ImageMvpConfig | None = None,
    controller: ImageMvpController | None = None,
) -> ImageMvpSurface:
    """Create an Agg-backed surface for component and live headless tests."""
    figure = Figure(figsize=(13.0, 9.0))
    FigureCanvasAgg(figure)
    axes_array = figure.subplots(2, 2)
    axes = tuple(cast(Axes, axes) for axes in np.asarray(axes_array, dtype=object).flat)
    typed_axes = cast(tuple[Axes, Axes, Axes, Axes], axes)
    figure.subplots_adjust(wspace=0.23, hspace=0.30, bottom=0.29, top=0.90)
    surface = ImageMvpSurface(
        figure,
        typed_axes,
        input_path,
        translator,
        config=config,
        controller=controller,
    )
    surface.attach_controls()
    return surface


def render_image_mvp_png(
    snapshot: ImageMvpSnapshot,
    output: Path,
    translator: Translator,
    *,
    dpi: int = 120,
    overwrite: bool = False,
) -> Path:
    """Render a ready or empty four-panel snapshot and publish it atomically."""
    if snapshot.state not in (ImageMvpState.READY, ImageMvpState.EMPTY):
        raise DomainValidationError("image MVP PNG requires a ready or empty snapshot")
    if not isinstance(output, Path):
        raise DomainValidationError("image MVP output must be a .png pathlib.Path")
    output = validate_local_path(output, field_name="output")
    if output.suffix.lower() != ".png":
        raise DomainValidationError("image MVP output must be a .png pathlib.Path")
    if type(dpi) is not int or not 72 <= dpi <= 600:
        raise DomainValidationError("image MVP dpi must be between 72 and 600")
    if type(overwrite) is not bool or not output.parent.is_dir():
        raise DomainValidationError("image MVP output options are invalid")
    if output.exists() and not overwrite:
        raise FileExistsError(output.name)

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{output.stem}.",
            suffix=".tmp",
            dir=output.parent,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
        figure = Figure(figsize=(12.0, 8.0), dpi=dpi)
        canvas = FigureCanvasAgg(figure)
        axes_array = figure.subplots(2, 2)
        figure.subplots_adjust(
            left=0.06,
            right=0.96,
            bottom=0.11,
            top=0.90,
            wspace=0.25,
            hspace=0.30,
        )
        axes = tuple(cast(Axes, axes) for axes in np.asarray(axes_array, dtype=object).flat)
        surface = ImageMvpSurface(
            figure,
            cast(tuple[Axes, Axes, Axes, Axes], axes),
            Path("input.png"),
            translator,
        )
        surface._draw(snapshot)
        cast(Any, canvas).print_png(temporary_path)
        surface.close()
        if temporary_path.stat().st_size == 0:
            raise OSError("renderer produced an empty PNG")
        if overwrite:
            os.replace(temporary_path, output)
            temporary_path = None
        else:
            os.link(temporary_path, output)
        return output
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def run_image_mvp_interactive(
    input_path: Path,
    translator: Translator,
    *,
    config: ImageMvpConfig | None = None,
    interval_ms: int = 33,
) -> None:
    """Open the temporary but complete FS-013 Matplotlib desktop surface."""
    if type(interval_ms) is not int or interval_ms < 10:
        raise DomainValidationError("image MVP interval must be at least 10 ms")
    import matplotlib.pyplot as plt

    figure, axes_array = plt.subplots(2, 2, figsize=(13.0, 9.0))
    axes = tuple(cast(Axes, axes) for axes in np.asarray(axes_array, dtype=object).flat)
    figure.subplots_adjust(wspace=0.23, hspace=0.30, bottom=0.29, top=0.90)
    surface = ImageMvpSurface(
        figure,
        cast(tuple[Axes, Axes, Axes, Axes], axes),
        input_path,
        translator,
        config=config,
    )
    surface.attach_controls()

    def update() -> None:
        snapshot = surface.poll()
        if snapshot.state is ImageMvpState.READY:
            surface.tick(interval_ms / 1000.0)

    timer = figure.canvas.new_timer(interval=interval_ms)
    timer.add_callback(update)
    timer.start()
    try:
        plt.show()
    finally:
        timer.stop()
        surface.close()


def _draw_raster(axes: Axes, raster: RasterImage, title: str) -> None:
    pixels = np.frombuffer(raster.pixels, dtype=np.uint8).reshape(raster.height, raster.width)
    axes.imshow(pixels, cmap="gray", vmin=0, vmax=255, origin="upper")
    axes.set_title(title)
    axes.set_axis_off()
