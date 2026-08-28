"""Disconnected or piecewise planar curve domain value."""

from dataclasses import dataclass

from ._validation import immutable_tuple
from .curve import Curve
from .errors import DomainValidationError


@dataclass(frozen=True, slots=True)
class PiecewiseCurve:
    """Independent curve segments with no implicit bridge between them."""

    segments: tuple[Curve, ...]

    def __post_init__(self) -> None:
        segments = immutable_tuple(self.segments, field_name="segments")
        if not segments:
            raise DomainValidationError("piecewise curve must contain at least one segment")
        if any(not isinstance(segment, Curve) for segment in segments):
            raise DomainValidationError("piecewise curve segments must be Curve values")
        object.__setattr__(self, "segments", segments)

    @property
    def segment_count(self) -> int:
        """Number of independent segments."""
        return len(self.segments)

    @property
    def sample_count(self) -> int:
        """Total number of samples without adding inter-segment bridge points."""
        return sum(segment.sample_count for segment in self.segments)
