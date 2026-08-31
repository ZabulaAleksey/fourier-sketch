"""Actual-state canonical circle walkthrough for FS-030."""

from dataclasses import dataclass
from enum import StrEnum
from math import cos, pi, sin

from fourier_sketch.domain import (
    Curve,
    DomainValidationError,
    EpicycleVector,
    FourierCoefficient,
    FourierSpectrum,
    Point2D,
)

from .diagnostic_epicycles import EpicycleFrame, EpicycleTimeline
from .freehand import build_freehand_timeline

CANONICAL_CIRCLE_LESSON_ID = "canonical_circle_v1"
CANONICAL_CIRCLE_SAMPLE_COUNT = 32
CANONICAL_CIRCLE_FREQUENCY = 1


class EducationalStep(StrEnum):
    SAMPLES = "samples"
    COEFFICIENT = "coefficient"
    CIRCLE_VECTOR = "circle_vector"
    CHAIN = "chain"
    ENDPOINT = "endpoint"
    TRACE = "trace"


class EducationalUnavailableReason(StrEnum):
    INACTIVE = "inactive"
    INVALID_LESSON = "invalid_lesson"
    SOURCE_MISMATCH = "source_mismatch"
    MISSING_FREQUENCY = "missing_frequency"
    MISALIGNED_STATE = "misaligned_state"


@dataclass(frozen=True, slots=True)
class CanonicalCircleLesson:
    lesson_id: str
    curve: Curve
    timeline: EpicycleTimeline

    def __post_init__(self) -> None:
        if self.lesson_id != CANONICAL_CIRCLE_LESSON_ID:
            raise DomainValidationError("canonical lesson id is invalid")
        if self.timeline.snapshot().original is not self.curve:
            raise DomainValidationError("canonical lesson timeline must own its curve")


@dataclass(frozen=True, slots=True)
class EducationalSnapshot:
    lesson_id: str
    step: EducationalStep
    step_index: int
    step_count: int
    frame: EpicycleFrame
    sample_index: int
    sample: Point2D
    coefficient: FourierCoefficient
    vector: EpicycleVector
    trace_count: int
    latest_trace: Point2D

    def __post_init__(self) -> None:
        if self.lesson_id != CANONICAL_CIRCLE_LESSON_ID:
            raise DomainValidationError("educational snapshot lesson id is invalid")
        if not isinstance(self.step, EducationalStep):
            raise DomainValidationError("educational step is invalid")
        if self.step_index != tuple(EducationalStep).index(self.step):
            raise DomainValidationError("educational step index is misaligned")
        if self.step_count != len(EducationalStep):
            raise DomainValidationError("educational step count is invalid")
        if not isinstance(self.frame, EpicycleFrame):
            raise DomainValidationError("educational snapshot frame is invalid")
        if (
            type(self.sample_index) is not int
            or not 0 <= self.sample_index < self.frame.original.sample_count
            or self.frame.original.points[self.sample_index] is not self.sample
        ):
            raise DomainValidationError("educational sample is not owned by the frame")
        if not any(
            self.coefficient is item for item in self.frame.selection.coefficients
        ):
            raise DomainValidationError("educational coefficient is not owned by the frame")
        if not any(self.vector is item for item in self.frame.chain.vectors):
            raise DomainValidationError("educational vector is not owned by the frame")
        if self.coefficient.frequency != CANONICAL_CIRCLE_FREQUENCY:
            raise DomainValidationError("educational coefficient frequency is invalid")
        if self.vector.frequency != self.coefficient.frequency:
            raise DomainValidationError("educational coefficient/vector mapping is invalid")
        if (
            self.trace_count != len(self.frame.trace)
            or self.latest_trace is not self.frame.trace[-1]
        ):
            raise DomainValidationError("educational trace mapping is invalid")
        if self.latest_trace != self.frame.chain.endpoint:
            raise DomainValidationError("educational trace must end at the actual endpoint")


@dataclass(frozen=True, slots=True)
class EducationalUnavailable:
    reason: EducationalUnavailableReason


EducationalProjection = EducationalSnapshot | EducationalUnavailable


def build_canonical_circle_lesson() -> CanonicalCircleLesson:
    """Build the accepted lesson through the ordinary Fourier timeline path."""

    points = tuple(
        Point2D(
            cos(2.0 * pi * index / CANONICAL_CIRCLE_SAMPLE_COUNT),
            sin(2.0 * pi * index / CANONICAL_CIRCLE_SAMPLE_COUNT),
        )
        for index in range(CANONICAL_CIRCLE_SAMPLE_COUNT)
    )
    curve = Curve(points, closed=True)
    timeline = build_freehand_timeline(curve, harmonic_count=1)
    return CanonicalCircleLesson(CANONICAL_CIRCLE_LESSON_ID, curve, timeline)


class EducationalModeSession:
    """Bounded step identity projected over an actual immutable frame."""

    def __init__(self) -> None:
        self._source: object | None = None
        self._original: Curve | None = None
        self._lesson_id: str | None = None
        self._step_index = 0
        self.clear()

    @property
    def active(self) -> bool:
        return self._source is not None

    @property
    def step(self) -> EducationalStep:
        return tuple(EducationalStep)[self._step_index]

    def enter(
        self,
        frame: EpicycleFrame,
        *,
        spectrum: FourierSpectrum,
        source: object,
        lesson_id: str,
    ) -> EducationalProjection:
        if self.active:
            raise DomainValidationError("Educational Mode is already active")
        if not isinstance(frame, EpicycleFrame) or not isinstance(spectrum, FourierSpectrum):
            raise DomainValidationError("Educational Mode requires frame and spectrum")
        if source is None:
            return EducationalUnavailable(EducationalUnavailableReason.SOURCE_MISMATCH)
        projection = self._project_values(frame, spectrum, lesson_id, 0)
        if isinstance(projection, EducationalUnavailable):
            return projection
        self._source = source
        self._original = frame.original
        self._lesson_id = lesson_id
        self._step_index = 0
        return projection

    def project(
        self,
        frame: EpicycleFrame,
        *,
        spectrum: FourierSpectrum,
        source: object,
        lesson_id: str,
    ) -> EducationalProjection:
        if not self.active:
            return EducationalUnavailable(EducationalUnavailableReason.INACTIVE)
        if not isinstance(frame, EpicycleFrame) or not isinstance(spectrum, FourierSpectrum):
            raise DomainValidationError("Educational Mode requires frame and spectrum")
        if (
            source is not self._source
            or frame.original is not self._original
            or lesson_id != self._lesson_id
        ):
            self.clear()
            return EducationalUnavailable(EducationalUnavailableReason.SOURCE_MISMATCH)
        projection = self._project_values(frame, spectrum, lesson_id, self._step_index)
        if isinstance(projection, EducationalUnavailable):
            self.clear()
        return projection

    def next(self) -> None:
        if not self.active:
            raise DomainValidationError("Educational Mode is not active")
        self._step_index = min(len(EducationalStep) - 1, self._step_index + 1)

    def previous(self) -> None:
        if not self.active:
            raise DomainValidationError("Educational Mode is not active")
        self._step_index = max(0, self._step_index - 1)

    def home(self) -> None:
        if not self.active:
            raise DomainValidationError("Educational Mode is not active")
        self._step_index = 0

    def clear(self) -> None:
        self._source = None
        self._original = None
        self._lesson_id = None
        self._step_index = 0

    @staticmethod
    def _project_values(
        frame: EpicycleFrame,
        spectrum: FourierSpectrum,
        lesson_id: str,
        step_index: int,
    ) -> EducationalProjection:
        if lesson_id != CANONICAL_CIRCLE_LESSON_ID:
            return EducationalUnavailable(EducationalUnavailableReason.INVALID_LESSON)
        if (
            frame.original.sample_count != CANONICAL_CIRCLE_SAMPLE_COUNT
            or spectrum.sample_count != CANONICAL_CIRCLE_SAMPLE_COUNT
            or frame.selection.coefficient_count != 1
        ):
            return EducationalUnavailable(EducationalUnavailableReason.MISALIGNED_STATE)
        spectrum_coefficient = next(
            (item for item in spectrum.coefficients if item.frequency == 1), None
        )
        selected_coefficient = next(
            (item for item in frame.selection.coefficients if item.frequency == 1), None
        )
        vector = next((item for item in frame.chain.vectors if item.frequency == 1), None)
        if spectrum_coefficient is None or selected_coefficient is None or vector is None:
            return EducationalUnavailable(EducationalUnavailableReason.MISSING_FREQUENCY)
        if selected_coefficient != spectrum_coefficient:
            return EducationalUnavailable(EducationalUnavailableReason.MISALIGNED_STATE)
        sample_index = (
            int(frame.chain.time * frame.original.sample_count)
            % frame.original.sample_count
        )
        return EducationalSnapshot(
            lesson_id,
            tuple(EducationalStep)[step_index],
            step_index,
            len(EducationalStep),
            frame,
            sample_index,
            frame.original.points[sample_index],
            selected_coefficient,
            vector,
            len(frame.trace),
            frame.trace[-1],
        )


__all__ = [
    "CANONICAL_CIRCLE_FREQUENCY",
    "CANONICAL_CIRCLE_LESSON_ID",
    "CANONICAL_CIRCLE_SAMPLE_COUNT",
    "CanonicalCircleLesson",
    "EducationalModeSession",
    "EducationalProjection",
    "EducationalSnapshot",
    "EducationalStep",
    "EducationalUnavailable",
    "EducationalUnavailableReason",
    "build_canonical_circle_lesson",
]
