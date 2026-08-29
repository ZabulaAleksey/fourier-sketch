from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from fourier_sketch.application import build_fft2_image, preprocess_local_image
from fourier_sketch.domain import DomainValidationError
from fourier_sketch.imaging import RasterImage, RasterStage


def test_existing_safe_grayscale_adapter_reaches_fft2(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    Image.fromarray(np.arange(24, dtype=np.uint8).reshape(4, 6), mode="L").save(source)
    raster = preprocess_local_image(source).grayscale
    result = build_fft2_image(raster)
    assert result.values.shape == (4, 6)
    assert result.reconstruct() == pytest.approx(result.values)


def test_oversized_raster_is_rejected_before_float_conversion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raster = RasterImage(2001, 2000, bytes(2001 * 2000), RasterStage.GRAYSCALE)
    called = False

    def fail_frombuffer(*_args: object, **_kwargs: object) -> np.ndarray:
        nonlocal called
        called = True
        raise AssertionError("conversion must not run")

    monkeypatch.setattr(np, "frombuffer", fail_frombuffer)
    with pytest.raises(DomainValidationError, match="pixel limit"):
        build_fft2_image(raster)
    assert not called
