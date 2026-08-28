"""Integration contracts for Curve through selection, reconstruction and metrics."""

from cmath import exp
from math import pi

import numpy as np
import pytest

from fourier_sketch.domain import Curve, NormalizedErrorStatus, Point2D, SpectrumOrdering
from fourier_sketch.math import (
    complex_samples_to_curve,
    curve_to_complex_samples,
    fft_dft,
    idft,
    reconstruct_samples,
    reconstruction_metrics,
    retained_energy_ratio,
    select_first,
    select_frequencies,
)

pytestmark = pytest.mark.integration

ABS_TOL = 1e-10


def test_full_selection_matches_idft_and_curve_round_trip() -> None:
    curve = Curve(
        tuple(Point2D(float(index), float(index * index - 2)) for index in range(7)),
        closed=False,
    )
    samples = curve_to_complex_samples(curve)
    spectrum = fft_dft(samples)
    selection = select_first(spectrum, spectrum.sample_count, SpectrumOrdering.INTERLEAVED)

    reconstructed = reconstruct_samples(selection)
    baseline = idft(spectrum)
    restored_curve = complex_samples_to_curve(reconstructed, closed=curve.closed)
    metrics = reconstruction_metrics(samples, reconstructed)

    assert np.allclose(reconstructed, baseline, atol=ABS_TOL, rtol=ABS_TOL)
    assert np.allclose(
        curve_to_complex_samples(restored_curve),
        samples,
        atol=ABS_TOL,
        rtol=ABS_TOL,
    )
    assert metrics.rmse <= ABS_TOL
    assert metrics.normalized_status is NormalizedErrorStatus.DEFINED
    assert retained_energy_ratio(selection, spectrum) == 1.0


def test_circle_partial_selection_reports_real_metrics_without_epicycles() -> None:
    sample_count = 32
    samples = tuple(exp(2j * pi * index / sample_count) for index in range(sample_count))
    spectrum = fft_dft(samples)
    selection = select_frequencies(spectrum, (1, 0))

    reconstructed = reconstruct_samples(selection)
    metrics = reconstruction_metrics(samples, reconstructed)

    assert np.allclose(reconstructed, samples, atol=ABS_TOL, rtol=ABS_TOL)
    assert selection.frequencies == (1, 0)
    assert metrics.rmse <= ABS_TOL
    assert retained_energy_ratio(selection, spectrum) == pytest.approx(1.0, abs=ABS_TOL)
