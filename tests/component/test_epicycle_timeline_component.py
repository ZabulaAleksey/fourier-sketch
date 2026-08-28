"""Component contracts for the diagnostic timeline and its presentation controls."""

from cmath import exp
from dataclasses import replace
from math import pi
from typing import cast

import pytest

from fourier_sketch.application import (
    EpicycleFrame,
    EpicycleTimeline,
    RenderVisibility,
    TimelineState,
)
from fourier_sketch.domain import Curve, DomainValidationError, Point2D, SpectrumOrdering
from fourier_sketch.math import fft_dft

pytestmark = pytest.mark.component


def make_timeline(*, harmonic_count: int = 3) -> EpicycleTimeline:
    sample_count = 16
    values = tuple(
        exp(2j * pi * index / sample_count) + 0.25 * exp(-4j * pi * index / sample_count)
        for index in range(sample_count)
    )
    curve = Curve(tuple(Point2D(value.real, value.imag) for value in values), closed=True)
    return EpicycleTimeline(
        fft_dft(values),
        curve,
        harmonic_count=harmonic_count,
        ordering=SpectrumOrdering.AMPLITUDE_DESCENDING,
    )


def test_play_pause_advance_and_restart_have_explicit_trace_semantics() -> None:
    timeline = make_timeline()
    initial = timeline.snapshot()
    assert initial.timeline_state is TimelineState.PAUSED
    assert initial.trace == (initial.chain.endpoint,)

    running = timeline.play()
    advanced = timeline.advance(0.25)
    assert running.timeline_state is TimelineState.RUNNING
    assert advanced.chain.time == pytest.approx(0.25)
    assert advanced.trace[-1] == advanced.chain.endpoint
    assert len(advanced.trace) == 2

    timeline.pause()
    paused = timeline.advance(2.0)
    assert paused.chain == advanced.chain
    assert paused.trace == advanced.trace

    restarted = timeline.restart()
    assert restarted.timeline_state is TimelineState.PAUSED
    assert restarted.chain.time == 0.0
    assert restarted.trace == (restarted.chain.endpoint,)


def test_speed_harmonic_and_visibility_controls_have_separate_effects() -> None:
    timeline = make_timeline()
    original = timeline.snapshot()

    speed_frame = timeline.set_speed(2.5)
    assert speed_frame.speed == 2.5
    assert speed_frame.chain == original.chain
    assert speed_frame.trace == original.trace

    timeline.play()
    moved = timeline.advance(0.2)
    assert moved.chain.time == pytest.approx(0.5)

    changed_count = timeline.set_harmonic_count(2)
    assert changed_count.selection.coefficient_count == 2
    assert changed_count.reconstruction.sample_count == changed_count.original.sample_count
    assert changed_count.trace == (changed_count.chain.endpoint,)

    chain_before_toggle = changed_count.chain
    toggled = timeline.set_visibility(circles=False, trace=False, original=False)
    assert toggled.visibility == RenderVisibility(
        circles=False,
        vectors=True,
        endpoint=True,
        trace=False,
        original=False,
        reconstruction=True,
    )
    assert toggled.chain == chain_before_toggle
    assert toggled.trace == changed_count.trace


@pytest.mark.parametrize("speed", [0.0, -1.0, 101.0, float("nan"), True])
def test_invalid_speed_is_rejected_without_state_change(speed: object) -> None:
    timeline = make_timeline()
    before = timeline.snapshot()

    with pytest.raises(DomainValidationError, match="speed"):
        timeline.set_speed(cast(float, speed))
    assert timeline.snapshot() == before


@pytest.mark.parametrize("count", [0, 17, -1, 1.5, True])
def test_invalid_harmonic_count_is_rejected(count: object) -> None:
    timeline = make_timeline()

    with pytest.raises(DomainValidationError, match="harmonic_count"):
        timeline.set_harmonic_count(cast(int, count))


def test_invalid_delta_visibility_and_explicit_ordering_are_rejected() -> None:
    timeline = make_timeline()
    with pytest.raises(DomainValidationError, match="delta_seconds"):
        timeline.advance(-0.1)
    with pytest.raises(DomainValidationError, match="unknown layer"):
        timeline.set_visibility(labels=False)
    with pytest.raises(DomainValidationError, match="booleans"):
        timeline.set_visibility(trace=cast(bool, 1))

    frame = timeline.snapshot()
    with pytest.raises(DomainValidationError, match="non-explicit"):
        EpicycleTimeline(
            fft_dft(tuple(complex(point.x, point.y) for point in frame.original.points)),
            frame.original,
            harmonic_count=1,
            ordering=SpectrumOrdering.EXPLICIT,
        )


def test_trace_budget_fails_closed_before_unbounded_growth(monkeypatch: pytest.MonkeyPatch) -> None:
    import fourier_sketch.application.diagnostic_epicycles as timeline_module

    monkeypatch.setattr(timeline_module, "MAX_TRACE_POINTS", 2)
    timeline = make_timeline()
    timeline.play()
    timeline.advance(0.1)

    with pytest.raises(DomainValidationError, match="trace"):
        timeline.advance(0.1)
    assert len(timeline.snapshot().trace) == 2


def test_frame_canonicalizes_trace_and_rejects_inconsistent_renderer_input() -> None:
    timeline = make_timeline()
    frame = timeline.snapshot()
    mutable_trace = list(frame.trace)

    copied = EpicycleFrame(
        chain=frame.chain,
        trace=cast(tuple[Point2D, ...], mutable_trace),
        visibility=frame.visibility,
        selection=frame.selection,
        original=frame.original,
        reconstruction=frame.reconstruction,
        timeline_state=frame.timeline_state,
        speed=frame.speed,
    )
    mutable_trace.append(Point2D(99.0, 99.0))
    assert isinstance(copied.trace, tuple)
    assert copied.trace == frame.trace

    with pytest.raises(DomainValidationError, match="latest trace"):
        replace(frame, trace=(Point2D(99.0, 99.0),))
    with pytest.raises(DomainValidationError, match="speed"):
        replace(frame, speed=cast(float, True))

    other_selection = timeline.set_harmonic_count(2).selection
    with pytest.raises(DomainValidationError, match="frequency order"):
        replace(frame, selection=other_selection)


def test_advance_failure_does_not_partially_mutate_timeline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import fourier_sketch.application.diagnostic_epicycles as timeline_module

    timeline = make_timeline()
    timeline.play()
    before = timeline.snapshot()

    def reject_chain(*_arguments: object, **_keywords: object) -> None:
        raise DomainValidationError("synthetic chain failure")

    monkeypatch.setattr(timeline_module, "build_epicycle_chain", reject_chain)
    with pytest.raises(DomainValidationError, match="synthetic chain failure"):
        timeline.advance(0.25)
    assert timeline.snapshot() == before


def test_harmonic_change_failure_does_not_partially_mutate_timeline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import fourier_sketch.application.diagnostic_epicycles as timeline_module

    timeline = make_timeline()
    before = timeline.snapshot()

    def reject_reconstruction(*_arguments: object, **_keywords: object) -> None:
        raise DomainValidationError("synthetic reconstruction failure")

    monkeypatch.setattr(timeline_module, "reconstruct_samples", reject_reconstruction)
    with pytest.raises(DomainValidationError, match="synthetic reconstruction failure"):
        timeline.set_harmonic_count(2)
    assert timeline.snapshot() == before
