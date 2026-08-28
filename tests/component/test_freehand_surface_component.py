"""Actual Matplotlib callback contracts for the FS-007 freehand surface."""

from typing import Any, cast

import pytest
from matplotlib.backend_bases import KeyEvent, MouseButton, MouseEvent

from fourier_sketch.application import CaptureState, FreehandCapture
from fourier_sketch.domain import DomainValidationError
from fourier_sketch.presentation import Translator
from fourier_sketch.render import (
    FreehandSurface,
    create_freehand_surface,
    run_freehand_interactive,
)

pytestmark = pytest.mark.component


def dispatch_pointer(
    surface: FreehandSurface,
    event_name: str,
    x: float,
    y: float,
) -> None:
    surface.figure.canvas.draw()
    pixel_x, pixel_y = surface.drawing_axes.transData.transform((x, y))
    event = MouseEvent(
        event_name,
        surface.figure.canvas,
        pixel_x,
        pixel_y,
        button=MouseButton.LEFT,
    )
    surface.figure.canvas.callbacks.process(event_name, event)


def test_actual_pointer_callbacks_build_timeline_and_endpoint_trace() -> None:
    surface = create_freehand_surface(
        Translator("en"),
        sample_count=32,
        harmonic_count=8,
        closed=False,
    )

    dispatch_pointer(surface, "button_press_event", -0.8, -0.5)
    dispatch_pointer(surface, "motion_notify_event", -0.2, 0.7)
    dispatch_pointer(surface, "motion_notify_event", 0.6, -0.1)
    dispatch_pointer(surface, "button_release_event", 0.6, -0.1)

    assert len(surface.callback_ids) == 4
    assert surface.capture_snapshot().state is CaptureState.READY
    assert surface.curve_result.sampled_curve.sample_count == 32
    assert surface.has_timeline
    frame = surface.tick(0.1)
    assert frame.trace[-1] == frame.chain.endpoint
    assert len(frame.trace) == 2


def test_outside_events_are_ignored_and_keyboard_reset_is_real_callback() -> None:
    surface = create_freehand_surface(Translator("en"), sample_count=8)
    outside = MouseEvent(
        "button_press_event",
        surface.figure.canvas,
        0,
        0,
        button=MouseButton.LEFT,
    )
    surface.figure.canvas.callbacks.process("button_press_event", outside)
    assert surface.capture_snapshot().state is CaptureState.EMPTY

    dispatch_pointer(surface, "button_press_event", 0.0, 0.0)
    dispatch_pointer(surface, "button_release_event", 0.0, 0.0)
    assert surface.has_timeline

    reset = KeyEvent("key_press_event", surface.figure.canvas, key="r")
    surface.figure.canvas.callbacks.process("key_press_event", reset)
    assert surface.capture_snapshot().state is CaptureState.EMPTY
    assert surface.has_timeline is False


def test_capture_limit_is_visible_and_does_not_publish_timeline() -> None:
    surface = create_freehand_surface(
        Translator("pseudo"),
        sample_count=8,
        capture=FreehandCapture(maximum_points=2),
    )

    dispatch_pointer(surface, "button_press_event", -0.5, 0.0)
    dispatch_pointer(surface, "motion_notify_event", 0.0, 0.5)
    dispatch_pointer(surface, "motion_notify_event", 0.5, 0.0)
    dispatch_pointer(surface, "button_release_event", 0.5, 0.0)

    assert surface.capture_snapshot().state is CaptureState.LIMIT_REACHED
    assert surface.has_timeline is False
    assert any("[!!" in text.get_text() for text in surface.drawing_axes.texts)


@pytest.mark.parametrize(
    ("field", "value"),
    (("sample_count", 0), ("harmonic_count", 129), ("speed", 0.0), ("closed", 1)),
)
def test_invalid_surface_options_fail_before_event_registration(field: str, value: object) -> None:
    options: dict[str, object] = {
        "sample_count": 128,
        "harmonic_count": 15,
        "speed": 1.0,
        "closed": False,
    }
    options[field] = value

    with pytest.raises(DomainValidationError):
        create_freehand_surface(Translator("en"), **cast(Any, options))


def test_invalid_collaborator_is_not_replaced_and_interactive_validation_precedes_figure() -> None:
    import matplotlib.pyplot as plt

    with pytest.raises(DomainValidationError, match="capture"):
        create_freehand_surface(
            Translator("en"),
            capture=cast(FreehandCapture, 0),
        )

    before = plt.get_fignums()
    with pytest.raises(DomainValidationError, match="translator"):
        run_freehand_interactive(cast(Translator, None))
    assert plt.get_fignums() == before
