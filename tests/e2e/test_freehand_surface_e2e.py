"""Live Matplotlib events → application → math → renderer → PNG evidence."""

from pathlib import Path

import pytest
from matplotlib.backend_bases import MouseButton, MouseEvent

from fourier_sketch.presentation import Translator
from fourier_sketch.render import FreehandSurface, create_freehand_surface, render_frame_png

pytestmark = pytest.mark.e2e


def dispatch(
    surface: FreehandSurface,
    event_name: str,
    coordinate: tuple[float, float],
) -> None:
    surface.figure.canvas.draw()
    pixel = surface.drawing_axes.transData.transform(coordinate)
    event = MouseEvent(
        event_name,
        surface.figure.canvas,
        pixel[0],
        pixel[1],
        button=MouseButton.LEFT,
    )
    surface.figure.canvas.callbacks.process(event_name, event)


def test_actual_freehand_event_path_produces_endpoint_png(tmp_path: Path) -> None:
    surface = create_freehand_surface(
        Translator("en"),
        sample_count=48,
        harmonic_count=10,
        closed=True,
    )
    points = ((-0.8, -0.2), (-0.3, 0.8), (0.7, 0.4), (0.5, -0.7), (-0.4, -0.8))

    dispatch(surface, "button_press_event", points[0])
    for point in points[1:]:
        dispatch(surface, "motion_notify_event", point)
    dispatch(surface, "button_release_event", points[-1])
    frames = tuple(surface.tick(1.0 / 30.0) for _ in range(12))
    output = tmp_path / "freehand.png"
    render_frame_png(frames[-1], output, Translator("en"))

    assert all(frame.trace[-1] == frame.chain.endpoint for frame in frames)
    assert surface.curve_result.sampled_curve.closed is True
    payload = output.read_bytes()
    assert payload.startswith(b"\x89PNG\r\n\x1a\n")
    assert payload.endswith(b"IEND\xaeB`\x82")
    assert len(payload) > 10_000
