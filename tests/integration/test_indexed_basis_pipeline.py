from fourier_sketch.application import IndexedBasisFrame, IndexedBasisTimeline, build_basis_timeline
from fourier_sketch.application.diagnostic_epicycles import TimelineState
from fourier_sketch.domain import BasisKind, Curve, Point2D


def _curve() -> Curve:
    return Curve((Point2D(0, 0), Point2D(1, 0), Point2D(1, 1)), closed=False)


def test_dct_and_walsh_adapters_keep_source_and_record_128_grid() -> None:
    for basis in (BasisKind.DCT_II, BasisKind.WALSH_HADAMARD):
        timeline = build_basis_timeline(_curve(), basis=basis)
        assert isinstance(timeline, IndexedBasisTimeline)
        frame = timeline.snapshot()
        assert isinstance(frame, IndexedBasisFrame)
        assert frame.basis is basis
        assert frame.source is timeline.source
        assert frame.analysis.sample_count == 128
        assert frame.term_count == 1


def test_indexed_timeline_completion_pauses_and_restart_returns_first_term() -> None:
    timeline = build_basis_timeline(_curve(), basis=BasisKind.DCT_II, speed=1.0)
    assert isinstance(timeline, IndexedBasisTimeline)
    timeline.play()
    complete = timeline.advance(32.0)
    assert complete.term_count == complete.total_terms == 128
    assert complete.state is TimelineState.PAUSED
    assert timeline.play().state is TimelineState.PAUSED
    assert timeline.restart().term_count == 1
