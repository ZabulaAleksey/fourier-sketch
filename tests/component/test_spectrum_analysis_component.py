"""Chart state and atomic publication evidence."""

from pathlib import Path

import pytest
from matplotlib.figure import Figure

from fourier_sketch.math import SpectrumAnalysis, analyze_spectrum, fft_dft
from fourier_sketch.presentation import Translator
from fourier_sketch.render import draw_spectrum_analysis, render_spectrum_analysis_png

pytestmark = pytest.mark.component


def _analysis() -> SpectrumAnalysis:
    samples = (0j, 1 + 0j, 0j, -1 + 0j)
    return analyze_spectrum(fft_dft(samples), samples, (1, 2, 4))


def test_chart_is_a_view_over_all_numeric_series() -> None:
    figure = Figure()
    axes = tuple(figure.subplots(1, 3))

    draw_spectrum_analysis(axes, _analysis(), Translator("en"))

    assert [len(axis.lines) for axis in axes] == [1, 1, 2]
    assert list(axes[2].lines[0].get_xdata()) == [1, 2, 4]


def test_png_is_atomic_and_preserves_existing_output(tmp_path: Path) -> None:
    output = tmp_path / "analysis.png"
    render_spectrum_analysis_png(_analysis(), output, Translator("en"))
    assert output.read_bytes().startswith(b"\x89PNG")
    with pytest.raises(FileExistsError):
        render_spectrum_analysis_png(_analysis(), output, Translator("en"))
