"""Unit contracts for the bounded FS-026 first-K state machine."""

from cmath import exp
from dataclasses import replace
from math import pi
from typing import cast

import pytest

from fourier_sketch.application import (
    BuildUpState,
    EpicycleTimeline,
    HarmonicBuildUpSession,
)
from fourier_sketch.domain import Curve, DomainValidationError, Point2D, SpectrumOrdering
from fourier_sketch.math import (
    build_epicycle_chain,
    fft_dft,
    reconstruct_samples,
    reconstruction_metrics,
    select_first,
)


def _timeline() -> EpicycleTimeline:
    count = 8
    values = tuple(
        exp(2j * pi * index / count) + 0.3 * exp(-4j * pi * index / count)
        for index in range(count)
    )
    curve = Curve(tuple(Point2D(value.real, value.imag) for value in values), closed=True)
    return EpicycleTimeline(
        fft_dft(values),
        curve,
        harmonic_count=4,
        ordering=SpectrumOrdering.AMPLITUDE_DESCENDING,
    )


def _assert_state(session: HarmonicBuildUpSession, expected: BuildUpState) -> None:
    assert session.state is expected


def test_first_k_steps_are_exact_and_leave_baseline_untouched() -> None:
    timeline = _timeline()
    baseline = timeline.snapshot()
    session = HarmonicBuildUpSession()
    started = session.enter(
        baseline,
        spectrum=timeline.complete_spectrum,
        source=timeline,
        ordering=SpectrumOrdering.INTERLEAVED,
        target_count=4,
        dwell_seconds=0.5,
    )

    assert started.state is BuildUpState.RUNNING
    assert started.frame.selection == select_first(
        timeline.complete_spectrum, 1, SpectrumOrdering.INTERLEAVED
    )
    assert started.frame.trace == (started.frame.chain.endpoint,)
    assert started.metrics.current_count == 1
    assert timeline.snapshot() == baseline

    session.advance(0.49)
    assert session.current_count == 1
    session.advance(0.01)
    second = session.project(baseline, source=timeline)
    assert second is not None
    assert second.metrics.current_count == 2
    assert second.frame.selection == select_first(
        timeline.complete_spectrum, 2, SpectrumOrdering.INTERLEAVED
    )
    assert second.frame.trace == (second.frame.chain.endpoint,)

    session.advance(99.0)
    assert session.current_count == 3
    assert timeline.snapshot() == baseline


def test_pause_play_restart_complete_and_exact_exit() -> None:
    timeline = _timeline()
    baseline = timeline.snapshot()
    session = HarmonicBuildUpSession()
    session.enter(
        baseline,
        spectrum=timeline.complete_spectrum,
        source=timeline,
        ordering=SpectrumOrdering.SIGNED,
        target_count=2,
        dwell_seconds=0.1,
    )
    session.pause()
    session.advance(1.0)
    assert session.current_count == 1
    _assert_state(session, BuildUpState.PAUSED)

    session.play()
    session.advance(0.1)
    assert session.current_count == 2
    _assert_state(session, BuildUpState.COMPLETED)
    session.play()
    _assert_state(session, BuildUpState.COMPLETED)

    session.restart()
    restarted = session.project(baseline, source=timeline)
    assert restarted is not None
    assert restarted.state is BuildUpState.PAUSED
    assert restarted.metrics.current_count == 1
    assert restarted.frame.trace == (restarted.frame.chain.endpoint,)

    restored = session.exit(baseline, source=timeline)
    assert restored is baseline
    assert not session.active


@pytest.mark.parametrize(
    ("ordering", "target", "dwell"),
    [
        (SpectrumOrdering.EXPLICIT, 2, 0.5),
        (SpectrumOrdering.SIGNED, 0, 0.5),
        (SpectrumOrdering.SIGNED, 9, 0.5),
        (SpectrumOrdering.SIGNED, 2, 0.09),
        (SpectrumOrdering.SIGNED, 2, 5.01),
        (SpectrumOrdering.SIGNED, 2, float("nan")),
    ],
)
def test_invalid_contract_is_transactional(
    ordering: SpectrumOrdering,
    target: int,
    dwell: float,
) -> None:
    timeline = _timeline()
    baseline = timeline.snapshot()
    session = HarmonicBuildUpSession()

    with pytest.raises(DomainValidationError, match="Build-Up"):
        session.enter(
            baseline,
            spectrum=timeline.complete_spectrum,
            source=timeline,
            ordering=ordering,
            target_count=target,
            dwell_seconds=dwell,
        )
    assert not session.active
    assert timeline.snapshot() == baseline


@pytest.mark.parametrize("delta", [-0.1, float("inf"), True])
def test_invalid_delta_preserves_active_step(delta: object) -> None:
    timeline = _timeline()
    session = HarmonicBuildUpSession()
    session.enter(
        timeline.snapshot(),
        spectrum=timeline.complete_spectrum,
        source=timeline,
        ordering=SpectrumOrdering.ABSOLUTE_FREQUENCY,
        target_count=3,
    )
    before = session.current_count
    with pytest.raises(DomainValidationError, match="delta_seconds"):
        session.advance(cast(float, delta))
    assert session.current_count == before


def test_source_mismatch_clears_without_retargeting() -> None:
    timeline = _timeline()
    baseline = timeline.snapshot()
    session = HarmonicBuildUpSession()
    session.enter(
        baseline,
        spectrum=timeline.complete_spectrum,
        source=timeline,
        ordering=SpectrumOrdering.SIGNED,
        target_count=3,
    )

    assert session.project(baseline, source=object()) is None
    assert not session.active


def test_projection_and_metrics_share_nonzero_origin_coordinates() -> None:
    timeline = _timeline()
    baseline = timeline.snapshot()
    origin = Point2D(2.5, -1.25)
    translated_original = Curve(
        tuple(
            Point2D(point.x + origin.x, point.y + origin.y)
            for point in baseline.original.points
        ),
        closed=baseline.original.closed,
    )
    translated_reconstruction = Curve(
        tuple(
            Point2D(point.x + origin.x, point.y + origin.y)
            for point in baseline.reconstruction.points
        ),
        closed=baseline.reconstruction.closed,
    )
    translated_chain = build_epicycle_chain(
        baseline.selection,
        baseline.chain.time,
        origin=origin,
    )
    translated = replace(
        baseline,
        chain=translated_chain,
        trace=(translated_chain.endpoint,),
        original=translated_original,
        reconstruction=translated_reconstruction,
    )
    session = HarmonicBuildUpSession()

    snapshot = session.enter(
        translated,
        spectrum=timeline.complete_spectrum,
        source=timeline,
        ordering=SpectrumOrdering.AMPLITUDE_DESCENDING,
        target_count=4,
    )

    raw_samples = reconstruct_samples(snapshot.frame.selection)
    display_samples = tuple(
        sample + complex(origin.x, origin.y) for sample in raw_samples
    )
    assert snapshot.frame.reconstruction.points[0] == Point2D(
        display_samples[0].real,
        display_samples[0].imag,
    )
    reference = tuple(
        complex(point.x, point.y) for point in translated_original.points
    )
    assert snapshot.metrics.reconstruction_metrics == reconstruction_metrics(
        reference,
        display_samples,
    )
