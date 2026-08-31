"""FS-030 localized canonical-equation formatting contracts."""

import pytest

from fourier_sketch.application import (
    EducationalModeSession,
    EducationalSnapshot,
    EducationalStep,
    build_canonical_circle_lesson,
)
from fourier_sketch.presentation import Translator, format_educational_copy

pytestmark = pytest.mark.unit


def test_each_step_formats_actual_values_and_pseudo_locale() -> None:
    lesson = build_canonical_circle_lesson()
    session = EducationalModeSession()
    session.enter(
        lesson.timeline.snapshot(),
        spectrum=lesson.timeline.complete_spectrum,
        source=lesson,
        lesson_id=lesson.lesson_id,
    )

    equations = []
    for _ in EducationalStep:
        snapshot = session.project(
            lesson.timeline.snapshot(),
            spectrum=lesson.timeline.complete_spectrum,
            source=lesson,
            lesson_id=lesson.lesson_id,
        )
        assert isinstance(snapshot, EducationalSnapshot)
        copy = format_educational_copy(snapshot, Translator("pseudo"))
        assert copy.title.startswith("[!! ")
        assert copy.body.startswith("[!! ")
        assert copy.equation.startswith("[!! ")
        assert "[missing:" not in copy.equation
        equations.append(copy.equation)
        session.next()

    assert any("+1.000000" in equation for equation in equations)
    assert len(set(equations)) == len(EducationalStep)
