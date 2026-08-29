"""Shared-signal evidence for both discontinuous presentation policies."""

import pytest

from fourier_sketch.application import (
    DiscontinuousMode,
    build_discontinuous_fourier,
    compare_discontinuous_with_forced_route,
)
from fourier_sketch.domain import Curve, PiecewiseCurve, Point2D

pytestmark = pytest.mark.integration


def _piecewise() -> PiecewiseCurve:
    return PiecewiseCurve(
        (
            Curve((Point2D(-2.0, 0.0), Point2D(-1.0, 1.0), Point2D(-1.0, -1.0)), closed=True),
            Curve((Point2D(1.0, 0.0), Point2D(2.0, 1.0), Point2D(2.0, -1.0)), closed=True),
        )
    )


def test_modes_share_samples_coefficients_and_endpoint_history() -> None:
    strict = build_discontinuous_fourier(
        _piecewise(), 32, harmonic_count=12, mode=DiscontinuousMode.STRICT_TRAJECTORY
    )
    pen_up = build_discontinuous_fourier(
        _piecewise(), 32, harmonic_count=12, mode=DiscontinuousMode.PEN_UP_RENDERING
    )

    assert strict.sampled == pen_up.sampled
    assert strict.spectrum == pen_up.spectrum
    assert strict.timeline.snapshot() == pen_up.timeline.snapshot()
    strict.timeline.play()
    pen_up.timeline.play()
    assert strict.timeline.advance(0.125) == pen_up.timeline.advance(0.125)


def test_forced_route_comparison_uses_same_budget_and_independent_timeline() -> None:
    discontinuous = build_discontinuous_fourier(_piecewise(), 32, harmonic_count=12)
    forced = Curve(
        (
            Point2D(-2.0, 0.0),
            Point2D(-1.0, 1.0),
            Point2D(-1.0, -1.0),
            Point2D(1.0, 0.0),
            Point2D(2.0, 1.0),
            Point2D(2.0, -1.0),
        ),
        closed=True,
    )

    comparison = compare_discontinuous_with_forced_route(discontinuous, forced)

    assert comparison.forced_curve.sample_count == discontinuous.spectrum.sample_count == 32
    assert comparison.forced_timeline.harmonic_count == discontinuous.timeline.harmonic_count
    assert comparison.forced_spectrum != discontinuous.spectrum
