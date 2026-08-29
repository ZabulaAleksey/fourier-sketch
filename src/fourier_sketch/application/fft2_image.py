"""FS-020 image-to-2D-spectrum application boundary."""

import numpy as np

from fourier_sketch.domain import DomainValidationError
from fourier_sketch.imaging import RasterImage, RasterStage
from fourier_sketch.math import MAX_FFT2_PIXELS, FFT2Image, FFT2MaskPolicy, fft2_image


def build_fft2_image(
    raster: RasterImage,
    *,
    policy: FFT2MaskPolicy = FFT2MaskPolicy.NONE,
    radius: float | None = None,
    selected: tuple[tuple[int, int], ...] = (),
) -> FFT2Image:
    if not isinstance(raster, RasterImage) or raster.stage is not RasterStage.GRAYSCALE:
        raise DomainValidationError("FS-020 requires a grayscale RasterImage")
    if raster.width * raster.height > MAX_FFT2_PIXELS:
        raise DomainValidationError("FFT2 raster exceeds pixel limit")
    values = (
        np.frombuffer(raster.pixels, dtype=np.uint8)
        .astype(np.float64)
        .reshape(raster.height, raster.width)
    )
    return fft2_image(values / 255.0, policy=policy, radius=radius, selected=selected)
