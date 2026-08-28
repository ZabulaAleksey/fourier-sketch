"""Component-level consumer contract for the assembled domain model."""

import pytest

from fourier_sketch.domain import (
    Curve,
    DomainValidationError,
    EpicycleChainState,
    EpicycleVector,
    FourierCoefficient,
    FourierSpectrum,
    Point2D,
)

pytestmark = pytest.mark.component


def test_domain_component_exposes_valid_state_and_typed_failure() -> None:
    origin = Point2D(0.0, 0.0)
    tip = Point2D(0.0, 1.0)
    curve = Curve(points=(origin, tip), closed=False)
    coefficient = FourierCoefficient(frequency=0, value=0.0 + 1.0j)
    spectrum = FourierSpectrum(coefficients=(coefficient,), sample_count=1)
    vector = EpicycleVector(0, 1.0, coefficient.phase, 0.0, 1.0j, origin, tip)
    state = EpicycleChainState(0.0, origin, (vector,), (origin,), tip)

    assert curve.start == state.origin
    assert spectrum.coefficients[0].amplitude == vector.amplitude
    assert state.endpoint == tip

    with pytest.raises(DomainValidationError, match="final vector end"):
        EpicycleChainState(0.0, origin, (vector,), (origin,), origin)
