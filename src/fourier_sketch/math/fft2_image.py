"""Typed, independent two-dimensional Fourier transform contracts."""

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from typing import cast

import numpy as np

from fourier_sketch.domain import DomainValidationError

from .errors import FourierBackendError

MAX_FFT2_PIXELS = 4_000_000


class FFT2MaskPolicy(StrEnum):
    NONE = "none"
    LOW_PASS = "low_pass"
    HIGH_PASS = "high_pass"
    SELECTED = "selected"


@dataclass(frozen=True, slots=True)
class FFT2Raster:
    height: int
    width: int
    values: np.ndarray

    def __post_init__(self) -> None:
        _dimensions(self.height, self.width)
        object.__setattr__(
            self,
            "values",
            _owned_array(self.values, np.float64, self.height, self.width, "values"),
        )


@dataclass(frozen=True, slots=True)
class FFT2Spectrum:
    height: int
    width: int
    coefficients: np.ndarray
    mask_policy: FFT2MaskPolicy = FFT2MaskPolicy.NONE
    radius: float | None = None
    selected_frequencies: tuple[tuple[int, int], ...] = ()
    axes: tuple[str, str] = ("row", "column")
    shift_convention: str = "unshifted_coefficients_fftshift_views"
    normalization: str = "backward"

    def __post_init__(self) -> None:
        _dimensions(self.height, self.width)
        coefficients = _owned_array(
            self.coefficients, np.complex128, self.height, self.width, "coefficients"
        )
        if not isinstance(self.mask_policy, FFT2MaskPolicy):
            raise DomainValidationError("FFT2 mask policy is invalid")
        if (
            self.axes != ("row", "column")
            or self.shift_convention != "unshifted_coefficients_fftshift_views"
            or self.normalization != "backward"
        ):
            raise DomainValidationError("FFT2 transform convention is invalid")
        selected = _selected(self.selected_frequencies, self.height, self.width)
        if self.radius is not None and (
            isinstance(self.radius, bool)
            or not isinstance(self.radius, (int, float))
            or not isfinite(float(self.radius))
            or self.radius < 0
        ):
            raise DomainValidationError("FFT2 radius must be finite and non-negative")
        object.__setattr__(self, "coefficients", coefficients)
        object.__setattr__(self, "radius", None if self.radius is None else float(self.radius))
        object.__setattr__(self, "selected_frequencies", selected)

    @property
    def shifted_magnitude(self) -> np.ndarray:
        return _readonly(np.fft.fftshift(np.abs(self.coefficients)))

    @property
    def shifted_log_magnitude(self) -> np.ndarray:
        return _readonly(np.log1p(self.shifted_magnitude))

    @property
    def shifted_phase(self) -> np.ndarray:
        return _readonly(np.angle(np.fft.fftshift(self.coefficients)))

    def reconstruct(self) -> np.ndarray:
        return ifft2_image(self)


@dataclass(frozen=True, slots=True)
class FFT2Image:
    raster: FFT2Raster
    spectrum: FFT2Spectrum

    def __post_init__(self) -> None:
        if not isinstance(self.raster, FFT2Raster) or not isinstance(self.spectrum, FFT2Spectrum):
            raise DomainValidationError("FFT2 image requires dedicated raster and spectrum values")
        if (self.raster.height, self.raster.width) != (self.spectrum.height, self.spectrum.width):
            raise DomainValidationError("FFT2 raster and spectrum dimensions must match")

    height = property(lambda self: self.raster.height)
    width = property(lambda self: self.raster.width)
    values = property(lambda self: self.raster.values)
    coefficients = property(lambda self: self.spectrum.coefficients)
    mask_policy = property(lambda self: self.spectrum.mask_policy)
    radius = property(lambda self: self.spectrum.radius)
    selected_frequencies = property(lambda self: self.spectrum.selected_frequencies)
    shifted_magnitude = property(lambda self: self.spectrum.shifted_magnitude)
    shifted_log_magnitude = property(lambda self: self.spectrum.shifted_log_magnitude)
    shifted_phase = property(lambda self: self.spectrum.shifted_phase)

    def reconstruct(self) -> np.ndarray:
        return ifft2_image(self.spectrum)


def ifft2_image(spectrum: FFT2Spectrum, *, imaginary_tolerance: float = 1e-10) -> np.ndarray:
    if not isinstance(spectrum, FFT2Spectrum):
        raise DomainValidationError("inverse FFT2 requires an FFT2Spectrum")
    if (
        isinstance(imaginary_tolerance, bool)
        or not isinstance(imaginary_tolerance, (int, float))
        or not isfinite(float(imaginary_tolerance))
        or imaginary_tolerance < 0
    ):
        raise DomainValidationError("imaginary tolerance must be finite and non-negative")
    try:
        reconstructed = np.fft.ifft2(spectrum.coefficients)
    except Exception as error:
        raise FourierBackendError("NumPy IFFT2 backend failed") from error
    if float(np.max(np.abs(reconstructed.imag))) > imaginary_tolerance:
        raise DomainValidationError("IFFT2 result is complex; selected mask lacks real symmetry")
    return _readonly(reconstructed.real)


def fft2_image(
    values: np.ndarray,
    *,
    policy: FFT2MaskPolicy = FFT2MaskPolicy.NONE,
    radius: float | None = None,
    selected: tuple[tuple[int, int], ...] = (),
) -> FFT2Image:
    try:
        raw = np.asarray(values)
    except (TypeError, ValueError, MemoryError) as error:
        raise DomainValidationError("FFT2 input must be a numeric 2D array") from error
    if raw.ndim != 2 or raw.size == 0 or raw.size > MAX_FFT2_PIXELS:
        raise DomainValidationError("FFT2 input must be a finite bounded 2D array")
    try:
        data = np.asarray(raw, dtype=np.float64)
    except (TypeError, ValueError, MemoryError) as error:
        raise DomainValidationError("FFT2 input must be numeric") from error
    if (
        data.ndim != 2
        or data.size == 0
        or data.size > MAX_FFT2_PIXELS
        or not np.isfinite(data).all()
    ):
        raise DomainValidationError("FFT2 input must be a finite bounded 2D array")
    if not isinstance(policy, FFT2MaskPolicy):
        raise DomainValidationError("FFT2 mask policy is invalid")
    selected = _selected(selected, data.shape[0], data.shape[1])
    if policy in (FFT2MaskPolicy.LOW_PASS, FFT2MaskPolicy.HIGH_PASS) and (
        radius is None
        or isinstance(radius, bool)
        or not isinstance(radius, (int, float))
        or not isfinite(float(radius))
        or radius < 0
    ):
        raise DomainValidationError("FFT2 pass filter requires non-negative finite radius")
    try:
        coeff = np.asarray(np.fft.fft2(data))
    except Exception as error:
        raise FourierBackendError("NumPy FFT2 backend failed") from error
    if policy is not FFT2MaskPolicy.NONE:
        if policy is FFT2MaskPolicy.SELECTED and not selected:
            raise DomainValidationError("selected FFT2 mask requires frequencies")
        fy = np.fft.fftfreq(data.shape[0])[:, None]
        fx = np.fft.fftfreq(data.shape[1])[None, :]
        distance = np.sqrt(fx * fx + fy * fy)
        if policy is FFT2MaskPolicy.LOW_PASS:
            mask = distance <= radius
        elif policy is FFT2MaskPolicy.HIGH_PASS:
            mask = distance >= radius
        else:
            mask = np.zeros(data.shape, dtype=bool)
            for row, col in selected:
                mask[row, col] = True
        coeff = np.where(mask, coeff, 0)
    raster = FFT2Raster(data.shape[0], data.shape[1], data)
    spectrum = FFT2Spectrum(
        data.shape[0], data.shape[1], coeff, policy, radius, tuple(selected)
    )
    return FFT2Image(raster, spectrum)


def _readonly(array: np.ndarray) -> np.ndarray:
    result = np.array(array, copy=True)
    result.setflags(write=False)
    return result


def _dimensions(height: int, width: int) -> None:
    if type(height) is not int or type(width) is not int or height < 1 or width < 1:
        raise DomainValidationError("FFT2 dimensions must be positive integers")
    if height * width > MAX_FFT2_PIXELS:
        raise DomainValidationError("FFT2 image exceeds pixel limit")


def _owned_array(
    array: np.ndarray,
    dtype: type[np.float64] | type[np.complex128],
    height: int,
    width: int,
    name: str,
) -> np.ndarray:
    if (
        not isinstance(array, np.ndarray)
        or array.shape != (height, width)
        or not np.issubdtype(array.dtype, np.number)
    ):
        raise DomainValidationError(f"FFT2 {name} shape or type is invalid")
    if not np.isfinite(array).all():
        raise DomainValidationError(f"FFT2 {name} must be finite")
    return _readonly(np.asarray(array, dtype=dtype))


def _selected(
    values: object, height: int, width: int
) -> tuple[tuple[int, int], ...]:
    try:
        raw: tuple[object, ...] = tuple(values)  # type: ignore[arg-type]
    except TypeError as error:
        raise DomainValidationError("selected FFT2 frequencies must be iterable") from error
    if any(
        not isinstance(item, tuple)
        or len(item) != 2
        or any(type(value) is not int for value in item)
        or not (0 <= item[0] < height and 0 <= item[1] < width)
        for item in raw
    ):
        raise DomainValidationError("selected FFT2 frequencies are invalid")
    selected = tuple(cast(tuple[int, int], item) for item in raw)
    if len(set(selected)) != len(selected):
        raise DomainValidationError("selected FFT2 frequencies must be unique")
    return selected
