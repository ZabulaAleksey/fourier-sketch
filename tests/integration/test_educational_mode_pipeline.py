"""FS-030 canonical fixture through actual Fourier/epicycle lesson state."""

import pytest

from fourier_sketch.application import (
    EducationalModeSession,
    EducationalSnapshot,
    build_canonical_circle_lesson,
)

pytestmark = pytest.mark.integration


def test_circle_to_spectrum_to_vector_to_endpoint_trace_pipeline() -> None:
    lesson = build_canonical_circle_lesson()
    timeline = lesson.timeline
    session = EducationalModeSession()
    frame = timeline.snapshot()
    entered = session.enter(
        frame,
        spectrum=timeline.complete_spectrum,
        source=lesson,
        lesson_id=lesson.lesson_id,
    )

    assert isinstance(entered, EducationalSnapshot)
    assert entered.coefficient in timeline.complete_spectrum.coefficients
    assert entered.coefficient is frame.selection.coefficients[0]
    assert entered.vector is frame.chain.vectors[0]
    assert entered.vector.start == frame.chain.origin
    assert entered.vector.end == frame.chain.endpoint
    assert entered.latest_trace == frame.chain.endpoint
