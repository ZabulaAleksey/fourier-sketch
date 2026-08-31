from math import pi

import pytest

from fourier_sketch.application import HarmonicPlaygroundSession, TimelineState
from fourier_sketch.domain import DomainValidationError, ManualHarmonic, SpectrumOrdering


def test_playground_builds_exact_explicit_order_timeline() -> None:
    session = HarmonicPlaygroundSession()
    session.upsert(ManualHarmonic(frequency=-2, amplitude=0.35, phase=pi / 4))

    timeline = session.build_timeline(speed=0.25)
    frame = timeline.snapshot()

    assert frame.selection.ordering is SpectrumOrdering.EXPLICIT
    assert frame.selection.frequencies == (1, -2)
    assert frame.selection.coefficients[0].value == pytest.approx(1 + 0j)
    assert frame.selection.coefficients[1].value == pytest.approx(
        0.35 * complex(2**-0.5, 2**-0.5)
    )
    assert frame.timeline_state is TimelineState.PAUSED
    assert frame.speed == 0.25
    assert len(frame.trace) == 1
    assert frame.trace[-1] == frame.chain.endpoint
    assert frame.original == frame.reconstruction


def test_playground_upsert_preserves_row_and_invalid_budget_is_transactional() -> None:
    session = HarmonicPlaygroundSession()
    session.upsert(ManualHarmonic(frequency=-2, amplitude=1.0, phase=0.0))
    session.upsert(ManualHarmonic(frequency=1, amplitude=4.0, phase=0.5))

    before = session.components
    assert tuple(component.frequency for component in before) == (1, -2)
    with pytest.raises(DomainValidationError, match="total amplitude"):
        session.upsert(ManualHarmonic(frequency=3, amplitude=4.0, phase=0.0))

    assert session.components == before


def test_playground_clear_requires_reset_or_component_before_build() -> None:
    session = HarmonicPlaygroundSession()
    session.clear()
    with pytest.raises(DomainValidationError, match="at least one"):
        session.build_timeline()

    session.reset_circle()
    assert session.build_timeline().snapshot().selection.frequencies == (1,)
