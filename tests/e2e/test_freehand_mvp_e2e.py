"""FS-008 live actual-events/controls endpoint-history milestone."""

from pathlib import Path

import pytest
from matplotlib.backend_bases import MouseButton, MouseEvent
from matplotlib.widgets import Button

from fourier_sketch.presentation import Translator
from fourier_sketch.render import FreehandSurface, create_freehand_surface, render_frame_png

pytestmark = pytest.mark.e2e


def dispatch(surface: FreehandSurface, event_name: str, point: tuple[float, float]) -> None:
    surface.figure.canvas.draw()
    pixel = surface.drawing_axes.transData.transform(point)
    event = MouseEvent(
        event_name,
        surface.figure.canvas,
        pixel[0],
        pixel[1],
        button=MouseButton.LEFT,
    )
    surface.figure.canvas.callbacks.process(event_name, event)


def click(surface: FreehandSurface, button: Button) -> None:
    surface.figure.canvas.draw()
    pixel = button.ax.transAxes.transform((0.5, 0.5))
    for event_name in ("button_press_event", "button_release_event"):
        event = MouseEvent(
            event_name,
            surface.figure.canvas,
            pixel[0],
            pixel[1],
            button=MouseButton.LEFT,
        )
        surface.figure.canvas.callbacks.process(event_name, event)


def test_one_surface_draw_controls_trace_and_png_are_the_same_live_path(tmp_path: Path) -> None:
    surface = create_freehand_surface(
        Translator("en"),
        sample_count=64,
        harmonic_count=12,
        closed=True,
    )
    points = ((-0.8, -0.2), (-0.4, 0.8), (0.6, 0.6), (0.8, -0.4), (-0.3, -0.8))
    dispatch(surface, "button_press_event", points[0])
    for point in points[1:]:
        dispatch(surface, "motion_notify_event", point)
    dispatch(surface, "button_release_event", points[-1])

    controls = surface.controls
    controls.speed_slider.set_val(1.75)
    assert controls.harmonic_slider is not None
    controls.harmonic_slider.set_val(10)
    zero_endpoint = surface.latest_frame.chain.endpoint
    click(surface, controls.play_button)
    frames = tuple(surface.tick(1.0 / 30.0) for _ in range(15))

    assert frames[-1].trace == (zero_endpoint, *(frame.chain.endpoint for frame in frames))
    assert frames[-1].speed == 1.75
    assert frames[-1].selection.coefficient_count == 10

    click(surface, controls.pause_button)
    paused_trace = surface.latest_frame.trace
    assert surface.tick(0.5).trace == paused_trace

    output = tmp_path / "freehand-mvp.png"
    render_frame_png(surface.latest_frame, output, Translator("en"))
    payload = output.read_bytes()
    assert payload.startswith(b"\x89PNG\r\n\x1a\n")
    assert payload.endswith(b"IEND\xaeB`\x82")
    assert len(payload) > 10_000
