"""Renderer-independent rotating-vector and head-to-tail chain mathematics."""

from cmath import exp
from math import isfinite, pi

from fourier_sketch.domain import (
    CoefficientSelection,
    DomainValidationError,
    EpicycleChainState,
    EpicycleVector,
    FourierCoefficient,
    Point2D,
)

from ._validation import finite_complex_value


def rotating_value(coefficient: FourierCoefficient, time: float) -> complex:
    """Evaluate one coefficient's rotating local vector at a finite periodic time."""
    if not isinstance(coefficient, FourierCoefficient):
        raise DomainValidationError("coefficient must be a FourierCoefficient")
    periodic_time, _ = _validated_time(time)
    angular_velocity = _angular_velocity(coefficient.frequency)
    value = coefficient.value * exp(1j * angular_velocity * periodic_time)
    return finite_complex_value(value, field_name="rotating vector")


def build_epicycle_chain(
    selection: CoefficientSelection,
    time: float,
    *,
    origin: Point2D | None = None,
) -> EpicycleChainState:
    """Build immutable head-to-tail geometry in the selection's exact order."""
    if not isinstance(selection, CoefficientSelection):
        raise DomainValidationError("selection must be a CoefficientSelection")
    if origin is None:
        chain_origin = Point2D(0.0, 0.0)
    elif isinstance(origin, Point2D):
        chain_origin = origin
    else:
        raise DomainValidationError("origin must be a Point2D")

    _, state_time = _validated_time(time)
    current = complex(chain_origin.x, chain_origin.y)
    vectors: list[EpicycleVector] = []

    for coefficient in selection.coefficients:
        local_value = rotating_value(coefficient, state_time)
        next_value = finite_complex_value(
            current + local_value,
            field_name="epicycle endpoint",
        )
        start = Point2D(current.real, current.imag)
        end = Point2D(next_value.real, next_value.imag)
        vectors.append(
            EpicycleVector(
                frequency=coefficient.frequency,
                amplitude=coefficient.amplitude,
                phase=coefficient.phase,
                angular_velocity=_angular_velocity(coefficient.frequency),
                local_value=local_value,
                start=start,
                end=end,
            )
        )
        current = next_value

    vector_values = tuple(vectors)
    return EpicycleChainState(
        time=state_time,
        origin=chain_origin,
        vectors=vector_values,
        centers=tuple(vector.start for vector in vector_values),
        endpoint=vector_values[-1].end,
    )


def _validated_time(time: float) -> tuple[float, float]:
    if isinstance(time, bool) or not isinstance(time, (int, float)):
        raise DomainValidationError("time must be a finite real number")
    try:
        state_time = float(time)
    except OverflowError as error:
        raise DomainValidationError("time must be finite") from error
    if not isfinite(state_time):
        raise DomainValidationError("time must be finite")
    return state_time % 1.0, state_time


def _angular_velocity(frequency: int) -> float:
    try:
        value = 2.0 * pi * frequency
    except OverflowError as error:
        raise DomainValidationError("angular velocity must be finite") from error
    if not isfinite(value):
        raise DomainValidationError("angular velocity must be finite")
    return value
