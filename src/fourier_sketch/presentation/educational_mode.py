"""Localized educational copy derived only from an actual projection."""

from dataclasses import dataclass

from fourier_sketch.application.educational_mode import EducationalSnapshot, EducationalStep
from fourier_sketch.domain import DomainValidationError

from .i18n import Translator


@dataclass(frozen=True, slots=True)
class EducationalCopy:
    title: str
    body: str
    equation: str


def format_educational_copy(
    snapshot: EducationalSnapshot, translator: Translator
) -> EducationalCopy:
    if not isinstance(snapshot, EducationalSnapshot) or not isinstance(translator, Translator):
        raise DomainValidationError("educational copy requires snapshot and translator")
    step = snapshot.step
    prefix = f"desktop.educational.step.{step.value}"
    values: dict[str, object]
    if step is EducationalStep.SAMPLES:
        values = {
            "index": snapshot.sample_index,
            "count": snapshot.frame.original.sample_count,
            "real": snapshot.sample.x,
            "imag": snapshot.sample.y,
        }
    elif step is EducationalStep.COEFFICIENT:
        values = {
            "frequency": snapshot.coefficient.frequency,
            "count": snapshot.frame.original.sample_count,
            "real": snapshot.coefficient.real,
            "imag": snapshot.coefficient.imaginary,
        }
    elif step is EducationalStep.CIRCLE_VECTOR:
        values = {
            "frequency": snapshot.vector.frequency,
            "real": snapshot.vector.local_value.real,
            "imag": snapshot.vector.local_value.imag,
            "amplitude": snapshot.vector.amplitude,
        }
    elif step is EducationalStep.CHAIN:
        values = {
            "frequency": snapshot.vector.frequency,
            "start_x": snapshot.vector.start.x,
            "start_y": snapshot.vector.start.y,
            "end_x": snapshot.vector.end.x,
            "end_y": snapshot.vector.end.y,
        }
    elif step is EducationalStep.ENDPOINT:
        values = {"x": snapshot.frame.chain.endpoint.x, "y": snapshot.frame.chain.endpoint.y}
    else:
        values = {
            "count_minus_one": snapshot.trace_count - 1,
            "count": snapshot.trace_count,
            "x": snapshot.latest_trace.x,
            "y": snapshot.latest_trace.y,
        }
    return EducationalCopy(
        translator.text(f"{prefix}.title"),
        translator.text(f"{prefix}.body"),
        translator.text(f"desktop.educational.equation.{step.value}", **values),
    )


__all__ = ["EducationalCopy", "format_educational_copy"]
