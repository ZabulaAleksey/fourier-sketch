"""Unit contracts for Point2D."""

from dataclasses import FrozenInstanceError

import pytest

from fourier_sketch.domain import DomainValidationError, Point2D

pytestmark = pytest.mark.unit


def test_point_normalizes_finite_coordinates_to_float() -> None:
    point = Point2D(2, -3.5)

    assert point.x == 2.0
    assert point.y == -3.5
    assert isinstance(point.x, float)


@pytest.mark.parametrize("coordinate", [float("nan"), float("inf"), float("-inf")])
def test_point_rejects_non_finite_coordinates(coordinate: float) -> None:
    with pytest.raises(DomainValidationError, match="finite"):
        Point2D(coordinate, 0.0)


def test_point_wraps_numeric_overflow_as_domain_validation() -> None:
    with pytest.raises(DomainValidationError, match="finite"):
        Point2D(10**400, 0.0)


def test_point_is_immutable() -> None:
    point = Point2D(1.0, 2.0)

    with pytest.raises(FrozenInstanceError):
        point.__setattr__("x", 3.0)
