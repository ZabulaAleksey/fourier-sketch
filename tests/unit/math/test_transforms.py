"""Analytical unit contracts for reference and FFT transforms."""

from cmath import exp
from math import pi
from typing import cast

import numpy as np
import pytest

from fourier_sketch.domain import DomainValidationError, FourierCoefficient, FourierSpectrum
from fourier_sketch.math import (
    MAX_FFT_SAMPLES,
    MAX_REFERENCE_SAMPLES,
    FourierBackendError,
    fft_dft,
    idft,
    reference_dft,
)

pytestmark = pytest.mark.unit

ABS_TOL = 1e-12  # Small analytical fixtures; accumulated error is O(N * machine epsilon).


def coefficient_values(spectrum: FourierSpectrum) -> dict[int, complex]:
    return {coefficient.frequency: coefficient.value for coefficient in spectrum.coefficients}


def test_reference_dft_constant_is_stationary_dc() -> None:
    spectrum = reference_dft((3.0 - 2.0j,) * 8)
    values = coefficient_values(spectrum)

    assert values[0] == pytest.approx(3.0 - 2.0j, abs=ABS_TOL)
    assert all(
        values[frequency] == pytest.approx(0.0j, abs=ABS_TOL)
        for frequency in values
        if frequency
    )


def test_reference_dft_circle_has_positive_first_harmonic() -> None:
    sample_count = 16
    samples = tuple(exp(2j * pi * index / sample_count) for index in range(sample_count))
    values = coefficient_values(reference_dft(samples))

    assert values[1] == pytest.approx(1.0 + 0.0j, abs=ABS_TOL)
    assert all(
        values[frequency] == pytest.approx(0.0j, abs=ABS_TOL)
        for frequency in values
        if frequency != 1
    )


def test_reference_dft_impulse_spreads_equal_coefficients() -> None:
    spectrum = reference_dft((1.0 + 0.0j, 0.0j, 0.0j, 0.0j))

    assert all(
        coefficient.value == pytest.approx(0.25 + 0.0j, abs=ABS_TOL)
        for coefficient in spectrum.coefficients
    )


def test_one_sample_round_trip_is_dc_only() -> None:
    spectrum = fft_dft((2.0 + 3.0j,))

    assert tuple(item.frequency for item in spectrum.coefficients) == (0,)
    assert idft(spectrum) == pytest.approx((2.0 + 3.0j,), abs=ABS_TOL)


def test_reference_dft_rejects_empty_non_finite_and_oversized_input() -> None:
    with pytest.raises(DomainValidationError, match="at least one"):
        reference_dft(())
    with pytest.raises(DomainValidationError, match="finite"):
        reference_dft((complex(float("inf"), 0.0),))
    with pytest.raises(DomainValidationError, match=str(MAX_REFERENCE_SAMPLES)):
        reference_dft((0.0j,) * (MAX_REFERENCE_SAMPLES + 1))


def test_fft_rejects_input_above_pre_allocation_budget() -> None:
    with pytest.raises(DomainValidationError, match=str(MAX_FFT_SAMPLES)):
        fft_dft((0.0j,) * (MAX_FFT_SAMPLES + 1))


def test_fft_backend_failure_is_explicit_without_reference_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_fft(_values: object) -> object:
        raise RuntimeError("backend unavailable")

    monkeypatch.setattr(np.fft, "fft", fail_fft)

    with pytest.raises(FourierBackendError, match="NumPy FFT"):
        fft_dft((1.0 + 0.0j,))


def test_inverse_fft_backend_failure_is_explicit_without_scalar_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spectrum = fft_dft((1.0 + 0.0j, 0.0j))

    def fail_ifft(_values: object) -> object:
        raise RuntimeError("backend unavailable")

    monkeypatch.setattr(np.fft, "ifft", fail_ifft)

    with pytest.raises(FourierBackendError, match="NumPy inverse FFT"):
        idft(spectrum)


def test_idft_requires_a_complete_spectrum() -> None:
    invalid = cast(FourierSpectrum, object())

    with pytest.raises(DomainValidationError, match="FourierSpectrum"):
        idft(invalid)


def test_idft_rejects_non_finite_reconstruction_result() -> None:
    spectrum = FourierSpectrum(
        coefficients=(
            FourierCoefficient(0, 1e308 + 0.0j),
            FourierCoefficient(-1, 1e308 + 0.0j),
        ),
        sample_count=2,
    )

    with pytest.raises(DomainValidationError, match="finite"):
        idft(spectrum)
