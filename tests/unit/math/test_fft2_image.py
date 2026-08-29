import numpy as np
import pytest

from fourier_sketch.domain import DomainValidationError
from fourier_sketch.math import FFT2MaskPolicy, FFT2Raster, FFT2Spectrum, fft2_image


def test_constant_has_only_dc_and_roundtrips() -> None:
    result = fft2_image(np.ones((4, 6)) * 3)
    assert result.coefficients[0, 0] == pytest.approx(72)
    assert np.count_nonzero(np.abs(result.coefficients) > 1e-10) == 1
    assert result.reconstruct() == pytest.approx(result.values)


def test_selected_mask_is_explicit_and_bounded() -> None:
    result = fft2_image(np.eye(4), policy=FFT2MaskPolicy.SELECTED, selected=((0, 0),))
    assert result.mask_policy is FFT2MaskPolicy.SELECTED
    assert np.count_nonzero(result.coefficients) == 1


def test_rejects_non_2d_and_missing_selection() -> None:
    with pytest.raises(DomainValidationError):
        fft2_image(np.ones(4))
    with pytest.raises(DomainValidationError):
        fft2_image(np.ones((2, 2)), policy=FFT2MaskPolicy.SELECTED)
    with pytest.raises(DomainValidationError):
        fft2_image(
            np.ones((2, 2)),
            policy=FFT2MaskPolicy.SELECTED,
            selected=[["x", "y"]],  # type: ignore[arg-type]
        )


def test_impulse_is_flat_and_sinusoid_has_expected_bins() -> None:
    impulse = np.zeros((4, 4))
    impulse[0, 0] = 1.0
    assert np.abs(fft2_image(impulse).coefficients) == pytest.approx(np.ones((4, 4)))
    columns = np.arange(8)
    sinusoid = np.tile(np.cos(2 * np.pi * columns / 8), (4, 1))
    coefficients = fft2_image(sinusoid).coefficients
    assert np.abs(coefficients[0, 1]) == pytest.approx(16.0)
    assert np.abs(coefficients[0, 7]) == pytest.approx(16.0)


def test_filters_record_parameters_and_arrays_are_immutable() -> None:
    result = fft2_image(np.eye(4), policy=FFT2MaskPolicy.LOW_PASS, radius=0.2)
    assert result.radius == 0.2
    with pytest.raises(ValueError):
        result.coefficients[0, 0] = 1
    high = fft2_image(np.eye(4), policy=FFT2MaskPolicy.HIGH_PASS, radius=0.2)
    assert np.count_nonzero(high.coefficients) < high.coefficients.size


def test_dedicated_types_record_convention_and_reject_complex_reconstruction() -> None:
    result = fft2_image(np.eye(4))
    assert isinstance(result.raster, FFT2Raster)
    assert isinstance(result.spectrum, FFT2Spectrum)
    assert result.spectrum.axes == ("row", "column")
    assert result.spectrum.normalization == "backward"
    assert result.spectrum.shift_convention == "unshifted_coefficients_fftshift_views"
    signal = np.tile(np.cos(2 * np.pi * np.arange(4) / 4), (4, 1))
    asymmetric = fft2_image(signal, policy=FFT2MaskPolicy.SELECTED, selected=((0, 1),))
    with pytest.raises(DomainValidationError, match="lacks real symmetry"):
        asymmetric.reconstruct()
