"""FS-009 method selection on the existing actual-event freehand surface."""

import pytest
from matplotlib.backend_bases import MouseButton, MouseEvent

from fourier_sketch.application import ResamplingMethod
from fourier_sketch.presentation import Translator
from fourier_sketch.render import FreehandSurface, create_freehand_surface

pytestmark = pytest.mark.component


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


def test_selector_rebuilds_the_same_ready_capture_and_reports_spacing() -> None:
    surface = create_freehand_surface(Translator("en"), sample_count=24, harmonic_count=8)
    points = ((-0.9, 0.0), (-0.8, 0.0), (0.0, 0.0), (0.9, 0.0))
    dispatch(surface, "button_press_event", points[0])
    for point in points[1:]:
        dispatch(surface, "motion_notify_event", point)
    dispatch(surface, "button_release_event", points[-1])
    indexed = surface.curve_result

    surface.controls.method_buttons.set_active(1)
    arc = surface.curve_result

    assert surface.resampling_method is ResamplingMethod.ARC_LENGTH
    assert arc.method is ResamplingMethod.ARC_LENGTH
    assert arc.source_curve == indexed.source_curve
    assert arc.sampled_spacing is not None
    assert indexed.sampled_spacing is not None
    assert arc.sampled_spacing.coefficient_of_variation < (
        indexed.sampled_spacing.coefficient_of_variation
    )
    assert surface.latest_frame.trace == (surface.latest_frame.chain.endpoint,)
    assert any("CV" in text.get_text() for text in surface.drawing_axes.texts)


def test_one_point_arc_length_selection_restores_valid_uniform_state() -> None:
    surface = create_freehand_surface(Translator("en"), sample_count=8, harmonic_count=8)
    point = (0.2, -0.3)
    dispatch(surface, "button_press_event", point)
    dispatch(surface, "button_release_event", point)
    previous = surface.latest_frame

    surface.controls.method_buttons.set_active(1)

    assert surface.resampling_method is ResamplingMethod.UNIFORM_INDEX
    assert surface.controls.method_buttons.value_selected == "Index"
    assert surface.latest_frame is previous
    assert surface.latest_frame.selection.coefficient_count == 1
