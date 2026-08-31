"""Unit contracts for the bounded FS-025 single-frequency analysis session."""

from cmath import exp
from math import pi

import pytest

from fourier_sketch.application import EpicycleTimeline, FrequencySoloSession, TimelineState
from fourier_sketch.domain import Curve, DomainValidationError, Point2D, SpectrumOrdering
from fourier_sketch.math import build_epicycle_chain, fft_dft, reconstruct_samples


def _timeline() -> EpicycleTimeline:
    sample_count = 16
    values = tuple(
        exp(2j * pi * index / sample_count)
        + 0.35 * exp(-4j * pi * index / sample_count)
        for index in range(sample_count)
    )
    curve = Curve(tuple(Point2D(value.real, value.imag) for value in values), closed=True)
    return EpicycleTimeline(
        fft_dft(values),
        curve,
        harmonic_count=4,
        ordering=SpectrumOrdering.AMPLITUDE_DESCENDING,
    )


def test_solo_projects_actual_one_frequency_set_and_restores_untouched_baseline() -> None:
    timeline = _timeline()
    session = FrequencySoloSession()
    baseline = timeline.snapshot()
    frequency = baseline.selection.frequencies[1]

    solo = session.enter(baseline, frequency, source=timeline)

    assert session.active
    assert session.frequency == frequency
    assert solo.selection.frequencies == (frequency,)
    assert solo.selection.ordering is SpectrumOrdering.EXPLICIT
    assert tuple(vector.frequency for vector in solo.chain.vectors) == (frequency,)
    assert solo.trace == (solo.chain.endpoint,)
    assert solo.timeline_state is baseline.timeline_state
    assert solo.speed == baseline.speed
    assert timeline.snapshot() == baseline

    timeline.play()
    advanced = timeline.advance(0.25)
    projected = session.project(advanced, source=timeline)
    assert projected.timeline_state is TimelineState.RUNNING
    assert projected.chain.time == advanced.chain.time
    assert len(projected.trace) == 2
    assert projected.trace[-1] == projected.chain.endpoint
    assert timeline.snapshot() == advanced

    restored = session.exit(advanced, source=timeline)
    assert not session.active
    assert session.frequency is None
    assert restored is advanced
    assert timeline.snapshot() == advanced


def test_restart_resets_solo_trace_without_changing_baseline_lifecycle() -> None:
    timeline = _timeline()
    session = FrequencySoloSession()
    frequency = timeline.snapshot().selection.frequencies[0]
    session.enter(timeline.snapshot(), frequency, source=timeline)
    timeline.play()
    session.project(timeline.advance(0.25), source=timeline)

    restarted = timeline.restart()
    solo = session.project(restarted, source=timeline)

    assert restarted.timeline_state is TimelineState.PAUSED
    assert solo.timeline_state is TimelineState.PAUSED
    assert solo.chain.time == 0.0
    assert solo.trace == (solo.chain.endpoint,)
    assert timeline.snapshot() == restarted


def test_same_time_frames_do_not_grow_solo_trace() -> None:
    timeline = _timeline()
    session = FrequencySoloSession()
    baseline = timeline.snapshot()
    first = session.enter(baseline, baseline.selection.frequencies[0], source=timeline)

    paused = session.project(timeline.pause(), source=timeline)
    speed = session.project(timeline.set_speed(0.5), source=timeline)
    visibility = session.project(timeline.set_visibility(circles=False), source=timeline)

    assert paused.trace == first.trace
    assert speed.trace == first.trace
    assert visibility.trace == first.trace
    assert timeline.snapshot().trace == baseline.trace


@pytest.mark.parametrize("frequency", [999, True, 1.5, None])
def test_invalid_or_stale_entry_is_rejected_without_hidden_session(
    frequency: object,
) -> None:
    timeline = _timeline()
    session = FrequencySoloSession()
    baseline = timeline.snapshot()

    with pytest.raises(DomainValidationError, match="frequency"):
        session.enter(baseline, frequency, source=timeline)  # type: ignore[arg-type]

    assert not session.active
    assert session.frequency is None
    assert timeline.snapshot() == baseline


def test_active_frequency_becoming_stale_clears_session_and_returns_baseline() -> None:
    timeline = _timeline()
    session = FrequencySoloSession()
    frequency = timeline.snapshot().selection.frequencies[-1]
    session.enter(timeline.snapshot(), frequency, source=timeline)

    smaller = timeline.set_harmonic_count(1)
    assert frequency not in smaller.selection.frequencies
    assert session.project(smaller, source=timeline) == smaller
    assert not session.active


def test_different_timeline_source_clears_session_without_retargeting() -> None:
    timeline = _timeline()
    session = FrequencySoloSession()
    baseline = timeline.snapshot()
    session.enter(baseline, baseline.selection.frequencies[0], source=timeline)
    replacement_timeline = _timeline()
    replacement = replacement_timeline.snapshot()

    assert replacement.original is not baseline.original
    assert session.project(replacement, source=replacement_timeline) is replacement
    assert not session.active


def test_projection_failure_is_transactional(monkeypatch: pytest.MonkeyPatch) -> None:
    import fourier_sketch.application.frequency_solo as solo_module

    timeline = _timeline()
    session = FrequencySoloSession()
    baseline = timeline.snapshot()

    def reject(*_args: object, **_kwargs: object) -> None:
        raise DomainValidationError("synthetic solo failure")

    monkeypatch.setattr(solo_module, "reconstruct_samples", reject)
    with pytest.raises(DomainValidationError, match="synthetic solo failure"):
        session.enter(baseline, baseline.selection.frequencies[0], source=timeline)
    assert not session.active
    assert timeline.snapshot() == baseline


def test_nonzero_origin_shifts_solo_chain_and_reconstruction_together() -> None:
    from dataclasses import replace

    timeline = _timeline()
    baseline = timeline.snapshot()
    origin = Point2D(3.0, 4.0)
    chain = build_epicycle_chain(baseline.selection, baseline.chain.time, origin=origin)
    shifted = replace(baseline, chain=chain, trace=(chain.endpoint,))
    session = FrequencySoloSession()
    frequency = shifted.selection.frequencies[0]

    solo = session.enter(shifted, frequency, source=timeline)

    expected_samples = tuple(
        sample + complex(origin.x, origin.y) for sample in reconstruct_samples(solo.selection)
    )
    actual_samples = tuple(complex(point.x, point.y) for point in solo.reconstruction.points)
    assert actual_samples == pytest.approx(expected_samples)
    assert complex(solo.chain.endpoint.x, solo.chain.endpoint.y) == pytest.approx(
        expected_samples[0]
    )


def test_owner_token_clears_identical_frame_from_another_timeline() -> None:
    timeline = _timeline()
    baseline = timeline.snapshot()
    session = FrequencySoloSession()
    session.enter(baseline, baseline.selection.frequencies[0], source=timeline)
    other_owner = object()

    assert session.project(baseline, source=other_owner) is baseline
    assert not session.active
