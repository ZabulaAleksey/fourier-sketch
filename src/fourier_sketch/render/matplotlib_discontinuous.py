"""Pen-up rendering for the discontinuous Fourier diagnostic."""

import os
import tempfile
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.axes import Axes

from fourier_sketch.application.discontinuous_fourier import (
    DiscontinuousFourierResult,
    DiscontinuousMode,
)
from fourier_sketch.application.local_paths import validate_local_path
from fourier_sketch.domain import DomainValidationError
from fourier_sketch.presentation import Translator


def render_discontinuous_png(
    result: DiscontinuousFourierResult,
    output: Path,
    translator: Translator,
    *,
    overwrite: bool = False,
) -> Path:
    if (
        not isinstance(result, DiscontinuousFourierResult)
        or not isinstance(output, Path)
        or not isinstance(translator, Translator)
    ):
        raise DomainValidationError("invalid discontinuous render arguments")
    output = validate_local_path(output, field_name="output")
    if output.suffix.lower() != ".png":
        raise DomainValidationError("output must use .png")
    if output.exists() and not overwrite:
        raise FileExistsError(output.name)
    figure, axes = plt.subplots(1, 2, figsize=(10, 4), dpi=120)
    try:
        draw_discontinuous_source(axes[0], result)
        axes[0].set_title(
            translator.text(f"discontinuous.panel.source.{result.mode.value}")
        )
        axes[0].set_aspect("equal")
        axes[1].plot(
            [p.value.real for p in result.spectrum.coefficients],
            [p.value.imag for p in result.spectrum.coefficients],
            ".",
        )
        axes[1].set_title(translator.text("discontinuous.panel.spectrum"))
        figure.suptitle(translator.text("discontinuous.preview.title", mode=result.mode.value))
        figure.tight_layout()
        with tempfile.NamedTemporaryFile(
            prefix=".discontinuous.", suffix=".tmp", dir=output.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)
        figure.savefig(temporary, format="png")
        os.replace(temporary, output) if overwrite else os.link(temporary, output)
        if not overwrite:
            temporary.unlink()
        return output
    finally:
        plt.close(figure)
        if "temporary" in locals() and temporary.exists():
            temporary.unlink()


def draw_discontinuous_source(axes: Axes, result: DiscontinuousFourierResult) -> None:
    """Draw either one strict signal trajectory or independent pen-up strokes."""
    if not isinstance(axes, Axes) or not isinstance(result, DiscontinuousFourierResult):
        raise DomainValidationError("invalid discontinuous source arguments")
    if result.mode is DiscontinuousMode.STRICT_TRAJECTORY:
        points = tuple(point for segment in result.curve.segments for point in segment.points)
        points += (points[0],)
        axes.plot([point.x for point in points], [point.y for point in points])
        return
    for segment in result.curve.segments:
        points = segment.points + ((segment.points[0],) if segment.closed else ())
        axes.plot([point.x for point in points], [point.y for point in points])
