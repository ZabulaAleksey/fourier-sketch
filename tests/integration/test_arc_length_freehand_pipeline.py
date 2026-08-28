"""FS-009 integration through capture, metrics, FFT timeline and endpoint trace."""

import pytest

from fourier_sketch.application import FreehandCapture, ResamplingMethod, build_freehand_timeline
from fourier_sketch.domain import DomainValidationError, Point2D

pytestmark = pytest.mark.integration


def test_same_nonuniform_capture_compares_methods_and_reaches_endpoint_trace() -> None:
    capture = FreehandCapture()
    points = (
        Point2D(0.0, 0.0),
        Point2D(0.1, 0.0),
        Point2D(1.0, 0.0),
        Point2D(4.0, 0.0),
    )
    capture.pointer_down(points[0])
    for point in points[1:]:
        capture.pointer_move(point)
    capture.pointer_up()

    indexed = capture.build_curve(
        sample_count=16,
        closed=False,
        method=ResamplingMethod.UNIFORM_INDEX,
    )
    arc = capture.build_curve(
        sample_count=16,
        closed=False,
        method=ResamplingMethod.ARC_LENGTH,
    )

    assert indexed.sampled_spacing is not None
    assert arc.sampled_spacing is not None
    assert arc.sampled_spacing.coefficient_of_variation < (
        indexed.sampled_spacing.coefficient_of_variation
    )
    timeline = build_freehand_timeline(arc.sampled_curve, harmonic_count=8)
    timeline.play()
    frames = tuple(timeline.advance(1.0 / 30.0) for _ in range(5))
    assert all(frame.trace[-1] == frame.chain.endpoint for frame in frames)


def test_arc_length_zero_total_does_not_fallback_to_index_method() -> None:
    capture = FreehandCapture()
    point = Point2D(2.0, -1.0)
    capture.pointer_down(point)
    capture.pointer_up()

    indexed = capture.build_curve(
        sample_count=8,
        closed=False,
        method=ResamplingMethod.UNIFORM_INDEX,
    )
    assert indexed.sampled_curve.sample_count == 1

    with pytest.raises(DomainValidationError, match="arc-length"):
        capture.build_curve(
            sample_count=8,
            closed=False,
            method=ResamplingMethod.ARC_LENGTH,
        )


def test_single_output_sample_keeps_method_and_typed_unavailable_spacing() -> None:
    capture = FreehandCapture()
    capture.pointer_down(Point2D(0.0, 0.0))
    capture.pointer_move(Point2D(2.0, 0.0))
    capture.pointer_up()

    for method in ResamplingMethod:
        result = capture.build_curve(sample_count=1, closed=False, method=method)
        assert result.method is method
        assert result.sampled_curve.sample_count == 1
        assert result.source_spacing is None
        assert result.sampled_spacing is None


def test_spacing_diagnostics_do_not_break_subnormal_index_baseline() -> None:
    capture = FreehandCapture()
    capture.pointer_down(Point2D(0.0, 0.0))
    capture.pointer_move(Point2D(5e-324, 0.0))
    capture.pointer_up()

    result = capture.build_curve(
        sample_count=3,
        closed=False,
        method=ResamplingMethod.UNIFORM_INDEX,
    )

    assert result.sampled_curve.start.x == 0.0
    assert result.sampled_curve.end.x == 5e-324
    assert result.source_spacing is None
    assert result.sampled_spacing is None
