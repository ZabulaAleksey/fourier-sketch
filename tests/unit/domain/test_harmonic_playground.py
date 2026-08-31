from math import pi

import pytest

from fourier_sketch.domain import DomainValidationError, ManualHarmonic


def test_manual_harmonic_exposes_exact_polar_coefficient() -> None:
    component = ManualHarmonic(frequency=-2, amplitude=0.35, phase=pi / 4)

    assert component.value.real == pytest.approx(0.35 / 2**0.5)
    assert component.value.imag == pytest.approx(0.35 / 2**0.5)


@pytest.mark.parametrize(
    ("frequency", "amplitude", "phase"),
    [
        (-65, 1.0, 0.0),
        (64, 1.0, 0.0),
        (1, 0.0, 0.0),
        (1, 4.01, 0.0),
        (1, 1.0, pi + 0.01),
        (1, float("nan"), 0.0),
    ],
)
def test_manual_harmonic_rejects_out_of_contract_values(
    frequency: int, amplitude: float, phase: float
) -> None:
    with pytest.raises(DomainValidationError):
        ManualHarmonic(frequency=frequency, amplitude=amplitude, phase=phase)
