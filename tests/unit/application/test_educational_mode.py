"""FS-030 actual-state educational session contracts."""

import pytest

from fourier_sketch.application import (
    CANONICAL_CIRCLE_FREQUENCY,
    EducationalModeSession,
    EducationalSnapshot,
    EducationalStep,
    EducationalUnavailable,
    EducationalUnavailableReason,
    build_canonical_circle_lesson,
)

pytestmark = pytest.mark.unit


def _projection(session: EducationalModeSession, lesson):  # type: ignore[no-untyped-def]
    return session.project(
        lesson.timeline.snapshot(),
        spectrum=lesson.timeline.complete_spectrum,
        source=lesson,
        lesson_id=lesson.lesson_id,
    )


def test_canonical_circle_uses_actual_paused_k_plus_one_timeline() -> None:
    lesson = build_canonical_circle_lesson()
    frame = lesson.timeline.snapshot()

    assert frame.original is lesson.curve
    assert frame.original.sample_count == 32
    assert frame.selection.frequencies == (CANONICAL_CIRCLE_FREQUENCY,)
    assert frame.chain.vectors[0].frequency == CANONICAL_CIRCLE_FREQUENCY
    assert frame.trace[-1] == frame.chain.endpoint


def test_six_steps_preserve_actual_aligned_values_and_bound_navigation() -> None:
    lesson = build_canonical_circle_lesson()
    session = EducationalModeSession()
    entered = session.enter(
        lesson.timeline.snapshot(),
        spectrum=lesson.timeline.complete_spectrum,
        source=lesson,
        lesson_id=lesson.lesson_id,
    )
    assert isinstance(entered, EducationalSnapshot)

    seen = []
    for _ in range(len(EducationalStep)):
        current = _projection(session, lesson)
        assert isinstance(current, EducationalSnapshot)
        seen.append(current.step)
        assert current.sample is current.frame.original.points[current.sample_index]
        assert current.coefficient is current.frame.selection.coefficients[0]
        assert current.vector is current.frame.chain.vectors[0]
        assert current.latest_trace is current.frame.trace[-1]
        assert current.latest_trace is current.frame.chain.endpoint
        session.next()

    assert seen == list(EducationalStep)
    assert session.step.value == EducationalStep.TRACE.value
    session.home()
    assert session.step.value == EducationalStep.SAMPLES.value
    session.previous()
    assert session.step.value == EducationalStep.SAMPLES.value


def test_project_updates_actual_animation_values_without_changing_step() -> None:
    lesson = build_canonical_circle_lesson()
    session = EducationalModeSession()
    session.enter(
        lesson.timeline.snapshot(),
        spectrum=lesson.timeline.complete_spectrum,
        source=lesson,
        lesson_id=lesson.lesson_id,
    )
    session.next()
    session.next()
    before = _projection(session, lesson)
    lesson.timeline.play()
    lesson.timeline.advance(0.125)
    after = _projection(session, lesson)

    assert isinstance(before, EducationalSnapshot)
    assert isinstance(after, EducationalSnapshot)
    assert before.step is after.step is EducationalStep.CIRCLE_VECTOR
    assert after.vector is after.frame.chain.vectors[0]
    assert after.vector.local_value != before.vector.local_value
    assert after.latest_trace is after.frame.chain.endpoint


def test_unavailable_projection_clears_without_partial_values() -> None:
    lesson = build_canonical_circle_lesson()
    session = EducationalModeSession()
    session.enter(
        lesson.timeline.snapshot(),
        spectrum=lesson.timeline.complete_spectrum,
        source=lesson,
        lesson_id=lesson.lesson_id,
    )

    mismatch = session.project(
        lesson.timeline.snapshot(),
        spectrum=lesson.timeline.complete_spectrum,
        source=object(),
        lesson_id=lesson.lesson_id,
    )

    assert mismatch == EducationalUnavailable(
        EducationalUnavailableReason.SOURCE_MISMATCH
    )
    assert not session.active
    assert _projection(session, lesson) == EducationalUnavailable(
        EducationalUnavailableReason.INACTIVE
    )


def test_invalid_entry_has_typed_unavailable_result_and_stays_inactive() -> None:
    lesson = build_canonical_circle_lesson()
    frame = lesson.timeline.set_harmonic_count(2)
    session = EducationalModeSession()

    result = session.enter(
        frame,
        spectrum=lesson.timeline.complete_spectrum,
        source=lesson,
        lesson_id=lesson.lesson_id,
    )

    assert result == EducationalUnavailable(
        EducationalUnavailableReason.MISALIGNED_STATE
    )
    assert not session.active
