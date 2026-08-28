"""Cartesian point domain value."""

from dataclasses import dataclass

from ._validation import finite_float


@dataclass(frozen=True, slots=True)
class Point2D:
    """An immutable finite point in the Cartesian plane."""

    x: float
    y: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "x", finite_float(self.x, field_name="x"))
        object.__setattr__(self, "y", finite_float(self.y, field_name="y"))
