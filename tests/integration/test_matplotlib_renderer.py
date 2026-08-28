"""Integration contracts for Matplotlib consuming actual application frames."""

from cmath import exp
from math import pi
from pathlib import Path
from typing import cast

import pytest
from matplotlib.axes import Axes
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.patches import Circle, FancyArrowPatch

from fourier_sketch.application import EpicycleFrame, EpicycleTimeline
from fourier_sketch.domain import Curve, DomainValidationError, Point2D, SpectrumOrdering
from fourier_sketch.math import fft_dft
from fourier_sketch.presentation import Translator
from fourier_sketch.render import draw_frame, render_frame_png, run_interactive

pytestmark = pytest.mark.integration


def make_frame() -> tuple[EpicycleTimeline, Translator]:
    sample_count = 24
    values = tuple(
        exp(2j * pi * index / sample_count) + 0.3 * exp(-4j * pi * index / sample_count)
        for index in range(sample_count)
    )
    curve = Curve(tuple(Point2D(value.real, value.imag) for value in values), closed=True)
    timeline = EpicycleTimeline(
        fft_dft(values),
        curve,
        harmonic_count=4,
        ordering=SpectrumOrdering.AMPLITUDE_DESCENDING,
    )
    timeline.play()
    timeline.advance(0.1)
    return timeline, Translator("en")


def test_renderer_consumes_chain_geometry_and_endpoint_trace() -> None:
    timeline, translator = make_frame()
    frame = timeline.snapshot()
    figure = Figure(figsize=(6.0, 6.0))
    FigureCanvasAgg(figure)
    axes = figure.subplots()

    draw_frame(axes, frame, translator)

    circles = [patch for patch in axes.patches if isinstance(patch, Circle)]
    arrows = [patch for patch in axes.patches if isinstance(patch, FancyArrowPatch)]
    assert len(circles) == frame.selection.coefficient_count
    assert len(arrows) == frame.selection.coefficient_count
    assert tuple((circle.center, circle.radius) for circle in circles) == tuple(
        ((vector.start.x, vector.start.y), vector.amplitude) for vector in frame.chain.vectors
    )
    assert frame.trace[-1] == frame.chain.endpoint


def test_visibility_hides_geometry_without_mutating_frame_math() -> None:
    timeline, translator = make_frame()
    before = timeline.snapshot()
    hidden = timeline.set_visibility(circles=False, vectors=False, endpoint=False, trace=False)
    figure = Figure(figsize=(6.0, 6.0))
    FigureCanvasAgg(figure)
    axes = figure.subplots()

    draw_frame(axes, hidden, translator)

    assert not any(isinstance(patch, (Circle, FancyArrowPatch)) for patch in axes.patches)
    assert hidden.chain == before.chain
    assert hidden.trace == before.trace


def test_png_writer_validates_destination_and_preserves_existing_file(tmp_path: Path) -> None:
    timeline, translator = make_frame()
    frame = timeline.snapshot()
    output = tmp_path / "diagnostic.png"

    render_frame_png(frame, output, translator)
    payload = output.read_bytes()
    assert payload.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(payload) > 10_000

    with pytest.raises(FileExistsError):
        render_frame_png(frame, output, translator)
    assert output.read_bytes() == payload

    with pytest.raises(DomainValidationError, match=r"\.png"):
        render_frame_png(frame, tmp_path / "diagnostic.jpg", translator)


def test_renderer_boundaries_reject_invalid_collaborators_before_use() -> None:
    timeline, translator = make_frame()
    frame = timeline.snapshot()
    figure = Figure(figsize=(6.0, 6.0))
    FigureCanvasAgg(figure)
    axes = figure.subplots()

    with pytest.raises(DomainValidationError, match="axes"):
        draw_frame(cast(Axes, None), frame, translator)
    with pytest.raises(DomainValidationError, match="frame"):
        draw_frame(axes, cast(EpicycleFrame, None), translator)
    with pytest.raises(DomainValidationError, match="translator"):
        draw_frame(axes, frame, cast(Translator, None))
    with pytest.raises(DomainValidationError, match="timeline"):
        run_interactive(cast(EpicycleTimeline, None), translator)
    with pytest.raises(DomainValidationError, match="translator"):
        run_interactive(timeline, cast(Translator, None))
