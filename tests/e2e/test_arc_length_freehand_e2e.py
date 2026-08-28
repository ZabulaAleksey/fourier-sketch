"""FS-009 actual events → method selector → arc-length → endpoint trace evidence."""

import pytest
from matplotlib.backend_bases import MouseButton, MouseEvent

from fourier_sketch.application import ResamplingMethod
from fourier_sketch.presentation import Translator
from fourier_sketch.render import FreehandSurface, create_freehand_surface

pytestmark = pytest.mark.e2e


def send(surface: FreehandSurface, event_name: str, point: tuple[float, float]) -> None:
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


def test_live_selector_uses_arc_length_curve_in_the_same_timeline() -> None:
    surface = create_freehand_surface(Translator("en"), sample_count=48, harmonic_count=10)
    points = ((-0.9, -0.5), (-0.8, -0.4), (-0.2, 0.4), (0.8, 0.6), (0.9, -0.6))
    send(surface, "button_press_event", points[0])
    for point in points[1:]:
        send(surface, "motion_notify_event", point)
    send(surface, "button_release_event", points[-1])
    indexed = surface.curve_result

    surface.controls.method_buttons.set_active(1)
    arc = surface.curve_result
    zero = surface.latest_frame.chain.endpoint
    frames = tuple(surface.tick(1.0 / 30.0) for _ in range(10))

    assert arc.method is ResamplingMethod.ARC_LENGTH
    assert indexed.sampled_spacing is not None
    assert arc.sampled_spacing is not None
    assert arc.sampled_spacing.coefficient_of_variation < (
        indexed.sampled_spacing.coefficient_of_variation
    )
    assert frames[-1].trace == (zero, *(frame.chain.endpoint for frame in frames))
