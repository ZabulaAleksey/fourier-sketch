"""Unit contracts for epicycle vector and chain-state values."""

from typing import cast

import pytest

from fourier_sketch.domain import (
    DomainValidationError,
    EpicycleChainState,
    EpicycleVector,
    Point2D,
)

pytestmark = pytest.mark.unit


def make_vector(
    start: Point2D,
    end: Point2D,
    *,
    frequency: int = 1,
) -> EpicycleVector:
    return EpicycleVector(
        frequency=frequency,
        amplitude=1.0,
        phase=0.0,
        angular_velocity=6.0,
        local_value=complex(end.x - start.x, end.y - start.y),
        start=start,
        end=end,
    )


def test_epicycle_vector_normalizes_and_exposes_geometry() -> None:
    start = Point2D(0.0, 0.0)
    end = Point2D(1.0, 0.0)
    vector = make_vector(start, end)

    assert vector.frequency == 1
    assert vector.amplitude == 1.0
    assert vector.local_value == 1.0 + 0.0j
    assert vector.start == start
    assert vector.end == end


def test_epicycle_vector_rejects_invalid_values() -> None:
    point = Point2D(0.0, 0.0)

    with pytest.raises(DomainValidationError, match="non-negative"):
        EpicycleVector(0, -1.0, 0.0, 0.0, 0.0j, point, point)
    with pytest.raises(DomainValidationError, match="finite"):
        EpicycleVector(0, 0.0, float("inf"), 0.0, 0.0j, point, point)

    invalid_point = cast(Point2D, object())
    with pytest.raises(DomainValidationError, match="Point2D"):
        EpicycleVector(0, 0.0, 0.0, 0.0, 0.0j, invalid_point, point)


def test_chain_state_accepts_connected_head_to_tail_vectors() -> None:
    origin = Point2D(0.0, 0.0)
    middle = Point2D(1.0, 0.0)
    endpoint = Point2D(1.0, 2.0)
    first = make_vector(origin, middle, frequency=0)
    second = make_vector(middle, endpoint, frequency=1)
    state = EpicycleChainState(
        time=0.25,
        origin=origin,
        vectors=(first, second),
        centers=(origin, middle),
        endpoint=endpoint,
    )

    assert state.vector_count == 2
    assert state.centers == tuple(vector.start for vector in state.vectors)
    assert state.endpoint == state.vectors[-1].end


def test_chain_state_rejects_empty_or_disconnected_vectors() -> None:
    origin = Point2D(0.0, 0.0)
    endpoint = Point2D(1.0, 0.0)

    with pytest.raises(DomainValidationError, match="at least one vector"):
        EpicycleChainState(0.0, origin, (), (), origin)

    first = make_vector(origin, endpoint)
    disconnected = make_vector(Point2D(2.0, 0.0), Point2D(3.0, 0.0))
    with pytest.raises(DomainValidationError, match="previous vector end"):
        EpicycleChainState(
            0.0,
            origin,
            (first, disconnected),
            (origin, disconnected.start),
            disconnected.end,
        )


def test_chain_state_rejects_malformed_collections_and_non_finite_time() -> None:
    origin = Point2D(0.0, 0.0)
    endpoint = Point2D(1.0, 0.0)
    vector = make_vector(origin, endpoint)
    invalid_vectors = cast(tuple[EpicycleVector, ...], None)
    invalid_centers = cast(tuple[Point2D, ...], None)

    with pytest.raises(DomainValidationError, match="vectors"):
        EpicycleChainState(0.0, origin, invalid_vectors, (origin,), endpoint)
    with pytest.raises(DomainValidationError, match="centers"):
        EpicycleChainState(0.0, origin, (vector,), invalid_centers, endpoint)
    with pytest.raises(DomainValidationError, match="finite"):
        EpicycleChainState(float("nan"), origin, (vector,), (origin,), endpoint)


def test_chain_state_rejects_inconsistent_origin_centers_or_endpoint() -> None:
    origin = Point2D(0.0, 0.0)
    endpoint = Point2D(1.0, 0.0)
    vector = make_vector(origin, endpoint)

    with pytest.raises(DomainValidationError, match="chain origin"):
        EpicycleChainState(0.0, Point2D(-1.0, 0.0), (vector,), (origin,), endpoint)
    with pytest.raises(DomainValidationError, match="center"):
        EpicycleChainState(0.0, origin, (vector,), (Point2D(2.0, 0.0),), endpoint)
    with pytest.raises(DomainValidationError, match="final vector end"):
        EpicycleChainState(0.0, origin, (vector,), (origin,), Point2D(2.0, 0.0))
