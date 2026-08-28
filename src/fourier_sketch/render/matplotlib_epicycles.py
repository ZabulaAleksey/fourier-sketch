"""Matplotlib adapter that consumes renderer-ready epicycle frames."""

import os
import tempfile
from pathlib import Path
from typing import Any, cast

from matplotlib.axes import Axes
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.patches import Circle, FancyArrowPatch

from fourier_sketch.application import EpicycleFrame, EpicycleTimeline, TimelineState
from fourier_sketch.domain import Curve, DomainValidationError, Point2D
from fourier_sketch.presentation import Translator


def draw_frame(axes: Axes, frame: EpicycleFrame, translator: Translator) -> None:
    """Draw one immutable frame without calculating any mathematical state."""
    if not isinstance(axes, Axes):
        raise DomainValidationError("axes must be a matplotlib Axes")
    if not isinstance(frame, EpicycleFrame):
        raise DomainValidationError("frame must be an EpicycleFrame")
    if not isinstance(translator, Translator):
        raise DomainValidationError("translator must be a Translator")

    axes.clear()
    visibility = frame.visibility
    if visibility.original:
        _draw_curve(
            axes,
            frame.original,
            color="#8b95a5",
            linewidth=1.2,
            linestyle=":",
            label=translator.text("legend.original"),
        )
    if visibility.reconstruction:
        _draw_curve(
            axes,
            frame.reconstruction,
            color="#2a9d8f",
            linewidth=1.4,
            linestyle="--",
            label=translator.text("legend.reconstruction"),
        )
    if visibility.trace:
        _draw_points(
            axes,
            frame.trace,
            color="#e76f51",
            linewidth=2.0,
            label=translator.text("legend.trace"),
        )
    if visibility.circles:
        for vector in frame.chain.vectors:
            axes.add_patch(
                Circle(
                    (vector.start.x, vector.start.y),
                    vector.amplitude,
                    fill=False,
                    linewidth=0.8,
                    edgecolor="#457b9d",
                    alpha=0.7,
                )
            )
    if visibility.vectors:
        for vector in frame.chain.vectors:
            axes.add_patch(
                FancyArrowPatch(
                    (vector.start.x, vector.start.y),
                    (vector.end.x, vector.end.y),
                    arrowstyle="-|>",
                    mutation_scale=10.0,
                    linewidth=1.1,
                    color="#1d3557",
                    shrinkA=0.0,
                    shrinkB=0.0,
                )
            )
    if visibility.endpoint:
        axes.scatter(
            (frame.chain.endpoint.x,),
            (frame.chain.endpoint.y,),
            color="#d00000",
            s=34.0,
            zorder=10,
            label=translator.text("legend.endpoint"),
        )

    axes.set_title(translator.text("app.title"))
    axes.set_xlabel(translator.text("axis.x"))
    axes.set_ylabel(translator.text("axis.y"))
    state_label = translator.text(
        "state.running" if frame.timeline_state is TimelineState.RUNNING else "state.paused"
    )
    axes.text(
        0.01,
        0.99,
        translator.text(
            "status.summary",
            state=state_label,
            time=frame.chain.time,
            harmonics=frame.selection.coefficient_count,
            speed=frame.speed,
        ),
        transform=axes.transAxes,
        ha="left",
        va="top",
        fontsize=9,
    )
    axes.grid(True, linewidth=0.4, alpha=0.3)
    axes.set_aspect("equal", adjustable="box")
    _fit_frame(axes, frame)
    handles, labels = axes.get_legend_handles_labels()
    if handles and labels:
        axes.legend(loc="lower right", fontsize=8)


def render_frame_png(
    frame: EpicycleFrame,
    output: Path,
    translator: Translator,
    *,
    dpi: int = 120,
    overwrite: bool = False,
) -> Path:
    """Render a PNG through Agg and publish it atomically at an explicit destination."""
    if not isinstance(output, Path):
        raise DomainValidationError("output must be a pathlib.Path")
    if output.suffix.lower() != ".png":
        raise DomainValidationError("output must use the .png extension")
    if isinstance(dpi, bool) or not isinstance(dpi, int) or dpi < 72 or dpi > 600:
        raise DomainValidationError("dpi must be an integer between 72 and 600")
    if not isinstance(overwrite, bool):
        raise DomainValidationError("overwrite must be a boolean")
    if not output.parent.is_dir():
        raise DomainValidationError("output parent directory must exist")
    if output.exists() and not overwrite:
        raise FileExistsError(output.name)

    temporary_path: Path | None = None
    reserved_destination = False
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{output.stem}.",
            suffix=".tmp",
            dir=output.parent,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)

        figure = Figure(figsize=(8.0, 8.0), layout="constrained")
        canvas = FigureCanvasAgg(figure)
        axes = figure.subplots()
        draw_frame(axes, frame, translator)
        cast_canvas = cast(Any, canvas)
        cast_canvas.print_png(temporary_path)
        if temporary_path.stat().st_size == 0:
            raise OSError("renderer produced an empty PNG")

        if not overwrite:
            with output.open("xb"):
                reserved_destination = True
        os.replace(temporary_path, output)
        temporary_path = None
        reserved_destination = False
        return output
    except Exception:
        if reserved_destination and output.exists():
            output.unlink()
        raise
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def run_interactive(
    timeline: EpicycleTimeline,
    translator: Translator,
    *,
    interval_ms: int = 33,
) -> None:
    """Open the temporary diagnostic UI backed by the same tested timeline/controller."""
    if not isinstance(timeline, EpicycleTimeline):
        raise DomainValidationError("timeline must be an EpicycleTimeline")
    if not isinstance(translator, Translator):
        raise DomainValidationError("translator must be a Translator")
    if isinstance(interval_ms, bool) or not isinstance(interval_ms, int) or interval_ms < 10:
        raise DomainValidationError("interval_ms must be an integer of at least 10")

    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation
    from matplotlib.widgets import Button, CheckButtons, Slider

    figure, axes = plt.subplots(figsize=(10.0, 8.0))
    figure.subplots_adjust(bottom=0.34)

    def redraw(frame: EpicycleFrame) -> None:
        draw_frame(axes, frame, translator)
        figure.canvas.draw_idle()

    play_button = Button(figure.add_axes((0.10, 0.23, 0.12, 0.05)), translator.text("control.play"))
    pause_button = Button(
        figure.add_axes((0.24, 0.23, 0.12, 0.05)),
        translator.text("control.pause"),
    )
    restart_button = Button(
        figure.add_axes((0.38, 0.23, 0.12, 0.05)),
        translator.text("control.restart"),
    )
    speed_slider = Slider(
        figure.add_axes((0.10, 0.15, 0.40, 0.035)),
        translator.text("control.speed"),
        0.1,
        timeline.maximum_speed,
        valinit=timeline.speed,
    )
    harmonic_slider: Slider | None = None
    if timeline.maximum_harmonics > 1:
        harmonic_slider = Slider(
            figure.add_axes((0.10, 0.08, 0.40, 0.035)),
            translator.text("control.harmonics"),
            1,
            timeline.maximum_harmonics,
            valinit=timeline.harmonic_count,
            valstep=1,
        )
    else:
        figure.text(
            0.10,
            0.09,
            f"{translator.text('control.harmonics')}: 1",
            fontsize=9,
        )
    layer_fields = (
        "circles",
        "vectors",
        "endpoint",
        "trace",
        "original",
        "reconstruction",
    )
    layer_labels = tuple(translator.text(f"control.{field}") for field in layer_fields)
    current_visibility = timeline.snapshot().visibility
    checks = CheckButtons(
        figure.add_axes((0.58, 0.07, 0.30, 0.20)),
        layer_labels,
        tuple(getattr(current_visibility, field) for field in layer_fields),
    )
    label_to_field = dict(zip(layer_labels, layer_fields, strict=True))

    play_button.on_clicked(lambda _event: redraw(timeline.play()))
    pause_button.on_clicked(lambda _event: redraw(timeline.pause()))
    restart_button.on_clicked(lambda _event: redraw(timeline.restart()))
    speed_slider.on_changed(lambda value: redraw(timeline.set_speed(float(value))))
    if harmonic_slider is not None:
        harmonic_slider.on_changed(lambda value: redraw(timeline.set_harmonic_count(int(value))))

    def toggle(label: str | None) -> None:
        if label is None:
            return
        field = label_to_field[label]
        visibility = timeline.snapshot().visibility
        redraw(timeline.set_visibility(**{field: not getattr(visibility, field)}))

    checks.on_clicked(toggle)

    def animate(_frame_index: int) -> tuple[Any, ...]:
        redraw(timeline.advance(interval_ms / 1000.0))
        return ()

    redraw(timeline.snapshot())
    animation = FuncAnimation(
        figure,
        animate,
        interval=interval_ms,
        cache_frame_data=False,
    )
    _ = animation
    plt.show()


def _draw_curve(
    axes: Axes,
    curve: Curve,
    *,
    color: str,
    linewidth: float,
    linestyle: str,
    label: str,
) -> None:
    points = curve.points + ((curve.start,) if curve.closed else ())
    _draw_points(
        axes,
        points,
        color=color,
        linewidth=linewidth,
        linestyle=linestyle,
        label=label,
    )


def _draw_points(
    axes: Axes,
    points: tuple[Point2D, ...],
    *,
    color: str,
    linewidth: float,
    label: str,
    linestyle: str = "-",
) -> None:
    axes.plot(
        tuple(point.x for point in points),
        tuple(point.y for point in points),
        color=color,
        linewidth=linewidth,
        linestyle=linestyle,
        label=label,
    )


def _fit_frame(axes: Axes, frame: EpicycleFrame) -> None:
    points: list[Point2D] = [
        *frame.original.points,
        *frame.reconstruction.points,
        *frame.trace,
        frame.chain.origin,
        frame.chain.endpoint,
    ]
    x_values = [point.x for point in points]
    y_values = [point.y for point in points]
    for vector in frame.chain.vectors:
        x_values.extend((vector.start.x - vector.amplitude, vector.start.x + vector.amplitude))
        y_values.extend((vector.start.y - vector.amplitude, vector.start.y + vector.amplitude))

    minimum_x, maximum_x = min(x_values), max(x_values)
    minimum_y, maximum_y = min(y_values), max(y_values)
    span = max(maximum_x - minimum_x, maximum_y - minimum_y, 1.0)
    margin = span * 0.1
    axes.set_xlim(minimum_x - margin, maximum_x + margin)
    axes.set_ylim(minimum_y - margin, maximum_y + margin)
