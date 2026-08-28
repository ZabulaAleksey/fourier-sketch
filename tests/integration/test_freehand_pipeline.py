"""Integration evidence for capture → Curve → FFT → timeline → endpoint trace."""

import pytest

from fourier_sketch.application import FreehandCapture, build_freehand_timeline
from fourier_sketch.domain import Point2D

pytestmark = pytest.mark.integration


def test_valid_freehand_curve_reaches_real_endpoint_timeline() -> None:
    capture = FreehandCapture()
    points = (
        Point2D(-1.0, 0.0),
        Point2D(0.0, 1.0),
        Point2D(1.0, 0.0),
        Point2D(0.0, -1.0),
    )
    capture.pointer_down(points[0])
    for point in points[1:]:
        capture.pointer_move(point)
    capture.pointer_up()

    result = capture.build_curve(sample_count=64, closed=True)
    timeline = build_freehand_timeline(result.sampled_curve, harmonic_count=12)
    timeline.play()
    frames = tuple(timeline.advance(1.0 / 30.0) for _ in range(8))

    assert result.sampled_curve.closed is True
    assert result.sampled_curve.sample_count == 64
    assert all(frame.trace[-1] == frame.chain.endpoint for frame in frames)
    assert len(frames[-1].trace) == 9
