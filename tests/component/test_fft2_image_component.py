"""FFT2 diagnostic artifact contract."""

from pathlib import Path

import numpy as np
import pytest

from fourier_sketch.math import fft2_image
from fourier_sketch.presentation import Translator
from fourier_sketch.render import render_fft2_png

pytestmark = pytest.mark.component


def test_renderer_writes_readable_atomic_png_and_preserves_existing(tmp_path: Path) -> None:
    output = tmp_path / "fft2.png"
    result = fft2_image(np.eye(8))

    rendered = render_fft2_png(result, output, Translator("pseudo"))

    assert rendered == output
    assert output.read_bytes().startswith(b"\x89PNG")
    with pytest.raises(FileExistsError):
        render_fft2_png(result, output, Translator("en"))
