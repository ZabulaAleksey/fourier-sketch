"""Analytical unit contracts for rotating vectors and epicycle chains."""

from itertools import pairwise
from math import atan2, pi
from typing import cast

import pytest

from fourier_sketch.domain import (
    CoefficientSelection,
    DomainValidationError,
    FourierCoefficient,
    Point2D,
    SpectrumOrdering,
)
from fourier_sketch.math import build_epicycle_chain, reconstruct_at, rotating_value

pytestmark = pytest.mark.unit

ABS_TOL = 1e-12


def make_selection(*coefficients: FourierCoefficient) -> CoefficientSelection:
    sample_count = max(3, len(coefficients))
    return CoefficientSelection(
        coefficients,
        sample_count=sample_count,
        ordering=SpectrumOrdering.EXPLICIT,
    )


def test_dc_vector_is_stationary_with_exact_properties() -> None:
    coefficient = FourierCoefficient(0, 3.0 + 4.0j)

    assert rotating_value(coefficient, 0.0) == 3.0 + 4.0j
    assert rotating_value(coefficient, 123.75) == 3.0 + 4.0j

    chain = build_epicycle_chain(make_selection(coefficient), 0.25)
    vector = chain.vectors[0]
    assert vector.amplitude == 5.0
    assert vector.phase == pytest.approx(atan2(4.0, 3.0))
    assert vector.angular_velocity == 0.0


def test_positive_and_negative_frequency_rotate_in_opposite_directions() -> None:
    positive = FourierCoefficient(1, 1.0 + 0.0j)
    negative = FourierCoefficient(-1, 1.0 + 0.0j)

    assert rotating_value(positive, 0.25) == pytest.approx(1.0j, abs=ABS_TOL)
    assert rotating_value(negative, 0.25) == pytest.approx(-1.0j, abs=ABS_TOL)
    assert rotating_value(positive, 4.25) == pytest.approx(1.0j, abs=ABS_TOL)
    assert build_epicycle_chain(make_selection(negative), 0.25).vectors[
        0
    ].angular_velocity == pytest.approx(-2.0 * pi)


def test_local_value_uses_amplitude_phase_and_rotation_formula() -> None:
    coefficient = FourierCoefficient(1, 2.0j)
    vector = build_epicycle_chain(make_selection(coefficient), 0.25).vectors[0]

    assert vector.local_value == pytest.approx(-2.0 + 0.0j, abs=ABS_TOL)
    assert vector.amplitude == pytest.approx(2.0)
    assert vector.phase == pytest.approx(pi / 2.0)
    assert vector.angular_velocity == pytest.approx(2.0 * pi)


def test_chain_preserves_order_connectivity_origin_and_endpoint_equivalence() -> None:
    selection = make_selection(
        FourierCoefficient(1, 1.0 + 0.0j),
        FourierCoefficient(0, 2.0 - 1.0j),
        FourierCoefficient(-1, 0.5 + 0.0j),
    )
    origin = Point2D(10.0, -4.0)
    chain = build_epicycle_chain(selection, 0.25, origin=origin)

    assert chain.time == 0.25
    assert chain.origin == origin
    assert tuple(vector.frequency for vector in chain.vectors) == (1, 0, -1)
    assert chain.centers == tuple(vector.start for vector in chain.vectors)
    assert all(
        current.start == previous.end
        for previous, current in pairwise(chain.vectors)
    )
    expected = complex(origin.x, origin.y) + reconstruct_at(selection, 0.25)
    assert complex(chain.endpoint.x, chain.endpoint.y) == pytest.approx(expected, abs=ABS_TOL)
    assert chain.endpoint == chain.vectors[-1].end
    assert all(
        complex(vector.end.x - vector.start.x, vector.end.y - vector.start.y)
        == pytest.approx(vector.local_value, abs=ABS_TOL)
        for vector in chain.vectors
    )
    assert all(
        vector.amplitude == pytest.approx(abs(vector.local_value), abs=ABS_TOL)
        for vector in chain.vectors
    )


def test_permutation_changes_intermediate_center_not_endpoint() -> None:
    first = FourierCoefficient(1, 1.0 + 0.0j)
    second = FourierCoefficient(0, 2.0j)
    forward = make_selection(first, second)
    reverse = make_selection(second, first)

    forward_chain = build_epicycle_chain(forward, 0.0)
    reverse_chain = build_epicycle_chain(reverse, 0.0)

    assert forward_chain.centers[1] != reverse_chain.centers[1]
    assert forward_chain.endpoint.x == pytest.approx(reverse_chain.endpoint.x, abs=ABS_TOL)
    assert forward_chain.endpoint.y == pytest.approx(reverse_chain.endpoint.y, abs=ABS_TOL)


@pytest.mark.parametrize("time", [float("nan"), float("inf"), True, "0"])
def test_epicycle_math_rejects_invalid_time(time: object) -> None:
    coefficient = FourierCoefficient(0, 1.0j)
    selection = make_selection(coefficient)

    with pytest.raises(DomainValidationError, match="time"):
        rotating_value(coefficient, cast(float, time))
    with pytest.raises(DomainValidationError, match="time"):
        build_epicycle_chain(selection, cast(float, time))


def test_epicycle_chain_rejects_invalid_origin() -> None:
    selection = make_selection(FourierCoefficient(0, 1.0j))

    with pytest.raises(DomainValidationError, match="origin"):
        build_epicycle_chain(selection, 0.0, origin=cast(Point2D, (0.0, 0.0)))


def test_unrepresentable_angular_velocity_is_a_typed_error() -> None:
    coefficient = FourierCoefficient(10**400, 1.0 + 0.0j)
    selection = CoefficientSelection(
        (coefficient,),
        sample_count=10**401,
        ordering=SpectrumOrdering.EXPLICIT,
    )

    with pytest.raises(DomainValidationError, match="angular velocity"):
        rotating_value(coefficient, 0.0)
    with pytest.raises(DomainValidationError, match="angular velocity"):
        build_epicycle_chain(selection, 0.0)
