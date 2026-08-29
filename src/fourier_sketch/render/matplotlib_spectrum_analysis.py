"""Numeric views for measured spectrum analysis."""

import os
import tempfile
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.axes import Axes

from fourier_sketch.application import DiscontinuitySpectrumComparison
from fourier_sketch.application.local_paths import validate_local_path
from fourier_sketch.domain import DomainValidationError
from fourier_sketch.math import SpectrumAnalysis
from fourier_sketch.presentation import Translator


def draw_spectrum_analysis(
    axes: tuple[Axes, Axes, Axes],
    analysis: SpectrumAnalysis | DiscontinuitySpectrumComparison,
    translator: Translator,
) -> None:
    if (
        len(axes) != 3
        or not isinstance(analysis, (SpectrumAnalysis, DiscontinuitySpectrumComparison))
        or not isinstance(translator, Translator)
    ):
        raise DomainValidationError("invalid spectrum analysis chart arguments")
    analyses = (
        (("discontinuous", analysis.discontinuous), ("continuous", analysis.continuous))
        if isinstance(analysis, DiscontinuitySpectrumComparison)
        else (("signal", analysis),)
    )
    for label, numeric in analyses:
        axes[0].plot(
            [p.frequency for p in numeric.points],
            [p.amplitude for p in numeric.points],
            ".-",
            label=label,
        )
        axes[1].plot(
            [p.frequency for p in numeric.points],
            [p.log_amplitude for p in numeric.points],
            ".-",
            label=label,
        )
        axes[2].plot(
            [item.k for item in numeric.sweep],
            [item.retained_energy_ratio for item in numeric.sweep],
            ".-",
            label=f"{label} energy",
        )
        axes[2].plot(
            [item.k for item in numeric.sweep],
            [item.reconstruction_metrics.rmse for item in numeric.sweep],
            ".-",
            label=f"{label} RMSE",
        )
    axes[0].set_title(translator.text("analysis.panel.amplitude"))
    axes[1].set_title(translator.text("analysis.panel.log_amplitude"))
    axes[2].set_title(translator.text("analysis.panel.k_sweep"))
    axes[2].legend()
    axes[0].legend()
    axes[1].legend()


def render_spectrum_analysis_png(
    analysis: SpectrumAnalysis | DiscontinuitySpectrumComparison,
    output: Path,
    translator: Translator,
    *,
    overwrite: bool = False,
) -> Path:
    if not isinstance(output, Path):
        raise DomainValidationError("output must be a Path")
    output = validate_local_path(output, field_name="output")
    if output.suffix.lower() != ".png":
        raise DomainValidationError("output must use .png")
    if output.exists() and not overwrite:
        raise FileExistsError(output.name)
    figure, axes = plt.subplots(1, 3, figsize=(13, 4), dpi=120)
    temporary: Path | None = None
    try:
        draw_spectrum_analysis(tuple(axes), analysis, translator)
        figure.tight_layout()
        with tempfile.NamedTemporaryFile(
            prefix=".spectrum-analysis.", suffix=".tmp", dir=output.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)
        figure.savefig(temporary, format="png")
        if overwrite:
            os.replace(temporary, output)
        else:
            os.link(temporary, output)
        return output
    finally:
        plt.close(figure)
        if temporary is not None and temporary.exists():
            temporary.unlink()
