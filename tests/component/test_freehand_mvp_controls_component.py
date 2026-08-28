"""Actual Matplotlib control contracts for the FS-008 cohesive MVP."""

import pytest
from matplotlib.backend_bases import MouseButton, MouseEvent
from matplotlib.widgets import Button

from fourier_sketch.application import TimelineState
from fourier_sketch.presentation import Translator
from fourier_sketch.render import FreehandSurface, create_freehand_surface

pytestmark = pytest.mark.component


def dispatch_stroke(surface: FreehandSurface) -> None:
    points = ((-0.8, -0.4), (-0.2, 0.7), (0.7, 0.2), (0.3, -0.7))
    for event_name, point in (
        ("button_press_event", points[0]),
        *(("motion_notify_event", point) for point in points[1:]),
        ("button_release_event", points[-1]),
    ):
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


def test_actual_controls_drive_the_captured_timeline_and_restart_trace() -> None:
    surface = create_freehand_surface(Translator("en"), sample_count=32, harmonic_count=8)
    controls = surface.controls

    controls.speed_slider.set_val(2.5)
    assert controls.harmonic_slider is not None
    controls.harmonic_slider.set_val(6)
    dispatch_stroke(surface)

    assert surface.latest_frame.speed == 2.5
    assert surface.latest_frame.selection.coefficient_count == 6
    click(surface, controls.pause_button)
    paused = surface.latest_frame
    assert paused.timeline_state is TimelineState.PAUSED
    assert surface.tick(0.25).trace == paused.trace

    click(surface, controls.play_button)
    advanced = surface.tick(0.25)
    assert advanced.timeline_state is TimelineState.RUNNING
    assert len(advanced.trace) == len(paused.trace) + 1

    source = surface.curve_result
    click(surface, controls.restart_button)
    assert surface.latest_frame.timeline_state is TimelineState.PAUSED
    assert len(surface.latest_frame.trace) == 1
    assert surface.curve_result == source


def test_controls_before_a_stroke_are_safe_and_do_not_fabricate_timeline() -> None:
    surface = create_freehand_surface(Translator("pseudo"), sample_count=16)

    click(surface, surface.controls.play_button)
    click(surface, surface.controls.pause_button)
    click(surface, surface.controls.restart_button)

    assert surface.has_timeline is False
    assert surface.render_axes.axison is False


def test_release_coordinate_is_captured_without_a_preceding_motion_event() -> None:
    surface = create_freehand_surface(Translator("en"), sample_count=8)
    points = ((-0.6, -0.4), (0.7, 0.5))

    for event_name, point in zip(
        ("button_press_event", "button_release_event"),
        points,
        strict=True,
    ):
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

    assert surface.capture_snapshot().points == surface.curve_result.source_curve.points
    assert surface.capture_snapshot().points[1].x == pytest.approx(points[1][0])
    assert surface.capture_snapshot().points[1].y == pytest.approx(points[1][1])


def test_sub_tenth_speed_widget_matches_the_timeline() -> None:
    surface = create_freehand_surface(
        Translator("en"),
        sample_count=8,
        harmonic_count=4,
        speed=0.05,
    )

    assert surface.controls.speed_slider.val == pytest.approx(0.05)
    dispatch_stroke(surface)
    assert surface.latest_frame.speed == pytest.approx(0.05)
    assert surface.controls.speed_slider.val == pytest.approx(surface.latest_frame.speed)


def test_one_point_dc_disables_and_truthfully_restores_harmonic_widget() -> None:
    surface = create_freehand_surface(
        Translator("en"),
        sample_count=8,
        harmonic_count=8,
    )
    point = (0.25, -0.5)
    for event_name in ("button_press_event", "button_release_event"):
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

    slider = surface.controls.harmonic_slider
    assert slider is not None
    assert slider.active is False
    assert slider.val == 1
    assert surface.latest_frame.selection.coefficient_count == 1

    slider.set_val(2)
    assert slider.val == 1
    assert surface.latest_frame.selection.coefficient_count == 1
