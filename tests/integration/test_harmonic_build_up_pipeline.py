"""Integration contract for spectrum ordering through FS-026 display frames."""

from cmath import exp
from math import pi

import pytest

from fourier_sketch.application import EpicycleTimeline, HarmonicBuildUpSession
from fourier_sketch.domain import Curve, Point2D, SpectrumOrdering
from fourier_sketch.math import fft_dft, reconstruct_at, select_first


def test_build_up_pipeline_preserves_prefix_endpoint_metrics_and_baseline() -> None:
    count = 12
    values = tuple(
        exp(2j * pi * index / count) + 0.2 * exp(6j * pi * index / count)
        for index in range(count)
    )
    curve = Curve(tuple(Point2D(value.real, value.imag) for value in values), closed=True)
    timeline = EpicycleTimeline(
        fft_dft(values),
        curve,
        harmonic_count=6,
        ordering=SpectrumOrdering.AMPLITUDE_DESCENDING,
    )
    baseline = timeline.snapshot()
    session = HarmonicBuildUpSession()
    session.enter(
        baseline,
        spectrum=timeline.complete_spectrum,
        source=timeline,
        ordering=SpectrumOrdering.INTERLEAVED,
        target_count=5,
        dwell_seconds=0.1,
    )

    for expected_k in range(1, 6):
        snapshot = session.project(baseline, source=timeline)
        assert snapshot is not None
        assert snapshot.frame.selection == select_first(
            timeline.complete_spectrum,
            expected_k,
            SpectrumOrdering.INTERLEAVED,
        )
        endpoint = complex(snapshot.frame.chain.endpoint.x, snapshot.frame.chain.endpoint.y)
        assert endpoint == pytest.approx(
            reconstruct_at(snapshot.frame.selection, baseline.chain.time), abs=1e-10
        )
        assert 0.0 <= snapshot.metrics.retained_energy_ratio <= 1.0
        assert snapshot.metrics.reconstruction_metrics.rmse >= 0.0
        assert snapshot.frame.trace == (snapshot.frame.chain.endpoint,)
        assert timeline.snapshot() == baseline
        if expected_k < 5:
            session.advance(0.1)
