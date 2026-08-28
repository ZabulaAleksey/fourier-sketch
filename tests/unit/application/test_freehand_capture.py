"""Unit contracts for bounded freehand capture and timeline composition."""

from typing import cast

import pytest

from fourier_sketch.application import (
    CaptureState,
    FreehandCapture,
    FreehandCaptureSnapshot,
    FreehandCurveResult,
    build_freehand_timeline,
)
from fourier_sketch.domain import Curve, DomainValidationError, Point2D

pytestmark = pytest.mark.unit


def test_capture_lifecycle_deduplicates_motion_and_builds_open_curve() -> None:
    capture = FreehandCapture(maximum_points=5)
    first = Point2D(0.0, 0.0)
    second = Point2D(1.0, 0.0)

    assert capture.snapshot().state is CaptureState.EMPTY
    assert capture.pointer_move(first).state is CaptureState.EMPTY
    assert capture.pointer_down(first).state is CaptureState.CAPTURING
    capture.pointer_move(first)
    capture.pointer_move(second)
    assert capture.pointer_up().state is CaptureState.READY

    result = capture.build_curve(sample_count=5, closed=False)
    assert result.captured_count == 2
    assert result.cleaned_count == 2
    assert result.sampled_curve.sample_count == 5
    assert result.sampled_curve.start == first
    assert result.sampled_curve.end == second
    assert result.method == "uniform_index"


def test_one_point_capture_builds_dc_only_timeline() -> None:
    capture = FreehandCapture()
    point = Point2D(2.0, -3.0)
    capture.pointer_down(point)
    capture.pointer_up()

    curve = capture.build_curve(sample_count=128, closed=True).sampled_curve
    timeline = build_freehand_timeline(curve)
    frame = timeline.snapshot()

    assert curve == Curve((point,), closed=True)
    assert frame.selection.coefficient_count == 1
    assert frame.chain.endpoint == point


def test_point_limit_fails_closed_until_reset() -> None:
    capture = FreehandCapture(maximum_points=2)
    capture.pointer_down(Point2D(0.0, 0.0))
    capture.pointer_move(Point2D(1.0, 0.0))

    limited = capture.pointer_move(Point2D(2.0, 0.0))

    assert limited.state is CaptureState.LIMIT_REACHED
    assert len(limited.points) == 2
    with pytest.raises(DomainValidationError, match="ready"):
        capture.build_curve(sample_count=2, closed=False)
    assert capture.reset().state is CaptureState.EMPTY
    assert capture.snapshot().points == ()


def test_cancel_clears_capture_without_fabricating_curve() -> None:
    capture = FreehandCapture()
    capture.pointer_down(Point2D(0.0, 0.0))

    cancelled = capture.cancel()

    assert cancelled.state is CaptureState.CANCELLED
    assert cancelled.points == ()
    with pytest.raises(DomainValidationError, match="ready"):
        capture.build_curve(sample_count=2, closed=False)


@pytest.mark.parametrize("maximum", [0, 10_001, 1.5, True])
def test_invalid_capture_budget_is_rejected(maximum: object) -> None:
    with pytest.raises(DomainValidationError, match="maximum_points"):
        FreehandCapture(maximum_points=cast(int, maximum))


def test_invalid_pointer_topology_and_harmonic_inputs_are_rejected() -> None:
    capture = FreehandCapture()
    with pytest.raises(DomainValidationError, match="Point2D"):
        capture.pointer_down(cast(Point2D, None))
    capture.pointer_down(Point2D(0.0, 0.0))
    capture.pointer_up()
    with pytest.raises(DomainValidationError, match="closed"):
        capture.build_curve(sample_count=1, closed=cast(bool, 1))
    curve = capture.build_curve(sample_count=1, closed=False).sampled_curve
    with pytest.raises(DomainValidationError, match="harmonic_count"):
        build_freehand_timeline(curve, harmonic_count=cast(int, True))


def test_public_capture_values_reject_inconsistent_state_and_counts() -> None:
    point = Point2D(0.0, 0.0)
    curve = Curve((point,), closed=False)

    with pytest.raises(DomainValidationError, match="cannot contain points"):
        FreehandCaptureSnapshot(CaptureState.EMPTY, (point,), 2)
    with pytest.raises(DomainValidationError, match="must contain points"):
        FreehandCaptureSnapshot(CaptureState.READY, (), 2)
    with pytest.raises(DomainValidationError, match="exactly maximum_points"):
        FreehandCaptureSnapshot(CaptureState.LIMIT_REACHED, (point,), 2)
    with pytest.raises(DomainValidationError, match="counts must be integers"):
        FreehandCurveResult(curve, curve, cast(int, True), 1)
    with pytest.raises(DomainValidationError, match="source curve sample_count"):
        FreehandCurveResult(curve, curve, 2, 2)
    with pytest.raises(DomainValidationError, match="counts are inconsistent"):
        FreehandCurveResult(curve, curve, 10_001, 1)
