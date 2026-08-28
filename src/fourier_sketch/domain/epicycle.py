"""Epicycle geometry domain values without rotation or rendering logic."""

from dataclasses import dataclass
from itertools import pairwise

from ._validation import finite_complex, finite_float, immutable_tuple, integer
from .errors import DomainValidationError
from .point import Point2D


@dataclass(frozen=True, slots=True)
class EpicycleVector:
    """A fully described vector in one head-to-tail chain state."""

    frequency: int
    amplitude: float
    phase: float
    angular_velocity: float
    local_value: complex
    start: Point2D
    end: Point2D

    def __post_init__(self) -> None:
        frequency = integer(self.frequency, field_name="frequency")
        amplitude = finite_float(self.amplitude, field_name="amplitude")
        if amplitude < 0:
            raise DomainValidationError("amplitude must be non-negative")

        if not isinstance(self.start, Point2D) or not isinstance(self.end, Point2D):
            raise DomainValidationError("vector start and end must be Point2D values")

        object.__setattr__(self, "frequency", frequency)
        object.__setattr__(self, "amplitude", amplitude)
        object.__setattr__(self, "phase", finite_float(self.phase, field_name="phase"))
        object.__setattr__(
            self,
            "angular_velocity",
            finite_float(self.angular_velocity, field_name="angular_velocity"),
        )
        object.__setattr__(
            self,
            "local_value",
            finite_complex(self.local_value, field_name="local_value"),
        )


@dataclass(frozen=True, slots=True)
class EpicycleChainState:
    """An immutable, structurally consistent head-to-tail vector-chain snapshot."""

    time: float
    origin: Point2D
    vectors: tuple[EpicycleVector, ...]
    centers: tuple[Point2D, ...]
    endpoint: Point2D

    def __post_init__(self) -> None:
        if not isinstance(self.origin, Point2D) or not isinstance(self.endpoint, Point2D):
            raise DomainValidationError("chain origin and endpoint must be Point2D values")

        vectors = immutable_tuple(self.vectors, field_name="vectors")
        centers = immutable_tuple(self.centers, field_name="centers")
        if not vectors:
            raise DomainValidationError("epicycle chain must contain at least one vector")
        if any(not isinstance(vector, EpicycleVector) for vector in vectors):
            raise DomainValidationError("chain vectors must be EpicycleVector values")
        if any(not isinstance(center, Point2D) for center in centers):
            raise DomainValidationError("chain centers must be Point2D values")
        if len(centers) != len(vectors):
            raise DomainValidationError("chain must contain one center per vector")
        if vectors[0].start != self.origin:
            raise DomainValidationError("the first vector must start at the chain origin")
        if centers != tuple(vector.start for vector in vectors):
            raise DomainValidationError("each chain center must equal its vector start")
        if any(current.start != previous.end for previous, current in pairwise(vectors)):
            raise DomainValidationError("each vector must start at the previous vector end")
        if self.endpoint != vectors[-1].end:
            raise DomainValidationError("chain endpoint must equal the final vector end")

        object.__setattr__(self, "time", finite_float(self.time, field_name="time"))
        object.__setattr__(self, "vectors", vectors)
        object.__setattr__(self, "centers", centers)

    @property
    def vector_count(self) -> int:
        """Number of vectors in this chain state."""
        return len(self.vectors)
