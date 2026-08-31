import pytest

from fourier_sketch.application import (
    HaarTimeline,
    build_basis_timeline,
    build_haar_timeline,
)
from fourier_sketch.application.diagnostic_epicycles import EpicycleTimeline, TimelineState
from fourier_sketch.domain import BasisKind, Curve, DomainValidationError, Point2D


def test_default_basis_adapter_preserves_existing_fourier_timeline_type() -> None:
    curve = Curve((Point2D(0, 0), Point2D(1, 0), Point2D(1, 1), Point2D(0, 1)), closed=True)
    timeline = build_basis_timeline(curve)

    assert isinstance(timeline, EpicycleTimeline)
    assert timeline.snapshot().original is curve


def test_haar_adapter_keeps_source_and_records_128_analysis_grid() -> None:
    curve = Curve((Point2D(0, 0), Point2D(2, 0), Point2D(2, 1)), closed=False)
    timeline = build_haar_timeline(curve)
    frame = timeline.snapshot()

    assert isinstance(timeline, HaarTimeline)
    assert frame.source is curve
    assert frame.analysis is not curve
    assert frame.analysis.sample_count == 128
    assert frame.decomposition.basis is BasisKind.HAAR_WAVELET
    assert frame.term_count == 1


def test_haar_animation_only_changes_active_term_count_and_restart() -> None:
    timeline = build_haar_timeline(
        Curve((Point2D(0, 0), Point2D(1, 0)), closed=False), speed=1.0
    )
    timeline.play()
    advanced = timeline.advance(0.5)

    assert advanced.state is TimelineState.RUNNING
    assert advanced.term_count == 3
    timeline.set_term_count(8)
    restarted = timeline.restart()
    assert restarted.term_count == 1
    assert restarted.source is advanced.source


def test_haar_animation_pauses_when_all_terms_are_active() -> None:
    timeline = build_haar_timeline(
        Curve((Point2D(0, 0), Point2D(1, 0)), closed=False), speed=1.0
    )
    timeline.play()
    frame = timeline.advance(32.0)

    assert frame.term_count == frame.total_terms == 128
    assert frame.state is TimelineState.PAUSED
    assert timeline.play().state is TimelineState.PAUSED


def test_running_haar_slider_to_full_selection_pauses() -> None:
    timeline = build_haar_timeline(
        Curve((Point2D(0, 0), Point2D(1, 0)), closed=False), speed=1.0
    )
    timeline.play()

    frame = timeline.set_term_count(timeline.maximum_terms)

    assert frame.term_count == frame.total_terms
    assert frame.state is TimelineState.PAUSED
    assert timeline.advance(1.0).state is TimelineState.PAUSED


@pytest.mark.parametrize("speed", [0.001, 1.001, 2.0])
def test_haar_adapter_rejects_speed_outside_desktop_contract(speed: float) -> None:
    curve = Curve((Point2D(0, 0), Point2D(1, 0)), closed=False)

    with pytest.raises(DomainValidationError, match="Haar speed"):
        build_haar_timeline(curve, speed=speed)


def test_haar_adapter_rejects_source_above_freehand_budget_before_resampling() -> None:
    curve = Curve(
        tuple(Point2D(float(index), float(index % 2)) for index in range(10_001)),
        closed=False,
    )

    with pytest.raises(DomainValidationError, match="10000"):
        build_haar_timeline(curve)
