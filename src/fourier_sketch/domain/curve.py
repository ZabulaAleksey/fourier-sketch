"""Ordered planar curve domain value."""

from dataclasses import dataclass

from ._validation import immutable_tuple
from .errors import DomainValidationError
from .point import Point2D


@dataclass(frozen=True, slots=True)
class Curve:
    """An immutable non-empty ordered sequence of planar samples."""

    points: tuple[Point2D, ...]
    closed: bool = False

    def __post_init__(self) -> None:
        points = immutable_tuple(self.points, field_name="points")
        if not points:
            raise DomainValidationError("curve must contain at least one point")
        if any(not isinstance(point, Point2D) for point in points):
            raise DomainValidationError("curve points must be Point2D values")
        if not isinstance(self.closed, bool):
            raise DomainValidationError("closed must be a boolean")
        object.__setattr__(self, "points", points)

    @property
    def sample_count(self) -> int:
        """Number of ordered samples in this curve."""
        return len(self.points)

    @property
    def start(self) -> Point2D:
        """First ordered point."""
        return self.points[0]

    @property
    def end(self) -> Point2D:
        """Last ordered point."""
        return self.points[-1]
