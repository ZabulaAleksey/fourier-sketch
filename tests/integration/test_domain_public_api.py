"""Integration contract for the public domain package boundary."""

import pytest

from fourier_sketch.domain import (
    Curve,
    EpicycleChainState,
    EpicycleVector,
    FourierCoefficient,
    FourierSpectrum,
    PiecewiseCurve,
    Point2D,
)

pytestmark = pytest.mark.integration


def test_public_domain_api_supports_a_complete_consumer_path() -> None:
    origin = Point2D(0.0, 0.0)
    endpoint = Point2D(1.0, 0.0)
    curve = Curve(points=(origin, endpoint))
    piecewise = PiecewiseCurve(segments=(curve,))
    coefficient = FourierCoefficient(frequency=0, value=1.0 + 0.0j)
    spectrum = FourierSpectrum(coefficients=(coefficient,), sample_count=1)
    vector = EpicycleVector(
        frequency=coefficient.frequency,
        amplitude=coefficient.amplitude,
        phase=coefficient.phase,
        angular_velocity=0.0,
        local_value=coefficient.value,
        start=origin,
        end=endpoint,
    )
    state = EpicycleChainState(
        time=0.0,
        origin=origin,
        vectors=(vector,),
        centers=(origin,),
        endpoint=endpoint,
    )

    assert piecewise.sample_count == curve.sample_count
    assert spectrum.coefficients[0] == coefficient
    assert state.endpoint == endpoint
