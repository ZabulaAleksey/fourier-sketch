"""Visible strict-versus-pen-up stroke policy evidence."""

import pytest
from matplotlib.figure import Figure

from fourier_sketch.application import DiscontinuousMode, build_discontinuous_fourier
from fourier_sketch.domain import Curve, PiecewiseCurve, Point2D
from fourier_sketch.render import draw_discontinuous_source

pytestmark = pytest.mark.component


def _result(mode: DiscontinuousMode):  # type: ignore[no-untyped-def]
    curve = PiecewiseCurve(
        (
            Curve((Point2D(0.0, 0.0), Point2D(1.0, 0.0))),
            Curve((Point2D(5.0, 0.0), Point2D(6.0, 0.0))),
        )
    )
    return build_discontinuous_fourier(curve, 16, mode=mode)


def test_pen_up_draws_segments_while_strict_draws_one_periodic_path() -> None:
    figure = Figure()
    pen_up_axes, strict_axes = figure.subplots(1, 2)

    draw_discontinuous_source(pen_up_axes, _result(DiscontinuousMode.PEN_UP_RENDERING))
    draw_discontinuous_source(strict_axes, _result(DiscontinuousMode.STRICT_TRAJECTORY))

    assert len(pen_up_axes.lines) == 2
    assert len(strict_axes.lines) == 1
    assert len(strict_axes.lines[0].get_xdata()) == 17
