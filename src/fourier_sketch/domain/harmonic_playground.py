"""Immutable user-authored Fourier harmonic values."""

from cmath import rect
from dataclasses import dataclass
from math import pi

from ._validation import finite_float, integer
from .errors import DomainValidationError

PLAYGROUND_SAMPLE_COUNT = 128
PLAYGROUND_MIN_FREQUENCY = -(PLAYGROUND_SAMPLE_COUNT // 2)
PLAYGROUND_MAX_FREQUENCY = (PLAYGROUND_SAMPLE_COUNT - 1) // 2
PLAYGROUND_MAX_AMPLITUDE = 4.0


@dataclass(frozen=True, slots=True)
class ManualHarmonic:
    """One exact polar Fourier coefficient authored by the user."""

    frequency: int
    amplitude: float
    phase: float

    def __post_init__(self) -> None:
        frequency = integer(self.frequency, field_name="harmonic frequency")
        amplitude = finite_float(self.amplitude, field_name="harmonic amplitude")
        phase = finite_float(self.phase, field_name="harmonic phase")
        if frequency < PLAYGROUND_MIN_FREQUENCY or frequency > PLAYGROUND_MAX_FREQUENCY:
            raise DomainValidationError(
                "harmonic frequency must belong to the canonical N=128 frequency set"
            )
        if amplitude <= 0.0 or amplitude > PLAYGROUND_MAX_AMPLITUDE:
            raise DomainValidationError(
                "harmonic amplitude must be greater than zero and at most 4"
            )
        if phase < -pi or phase > pi:
            raise DomainValidationError("harmonic phase must be between -pi and pi")
        object.__setattr__(self, "frequency", frequency)
        object.__setattr__(self, "amplitude", amplitude)
        object.__setattr__(self, "phase", phase)

    @property
    def value(self) -> complex:
        """Return the exact complex coefficient represented by the polar fields."""

        return rect(self.amplitude, self.phase)
