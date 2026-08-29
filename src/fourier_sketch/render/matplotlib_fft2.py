"""Headless diagnostic renderer for FS-020."""

import os
import tempfile
from pathlib import Path

import matplotlib.pyplot as plt

from fourier_sketch.application.local_paths import safe_display_basename, validate_local_path
from fourier_sketch.domain import DomainValidationError
from fourier_sketch.math import FFT2Image
from fourier_sketch.presentation import Translator


def render_fft2_png(
    result: FFT2Image,
    destination: Path,
    translator: Translator,
    *,
    overwrite: bool = False,
) -> Path:
    if not isinstance(result, FFT2Image) or not isinstance(destination, Path) or not isinstance(
        translator, Translator
    ):
        raise DomainValidationError("invalid FFT2 render arguments")
    path = validate_local_path(destination, field_name="output")
    if path.suffix.lower() != ".png":
        raise DomainValidationError("output must use .png")
    if path.exists() and not overwrite:
        raise FileExistsError(safe_display_basename(path))
    fig, axes = plt.subplots(1, 3, figsize=(10, 3))
    temporary: Path | None = None
    try:
        axes[0].imshow(result.values, cmap="gray", vmin=0, vmax=1)
        axes[0].set_title(translator.text("fft2.panel.input"))
        axes[1].imshow(result.shifted_log_magnitude, cmap="magma")
        axes[1].set_title(translator.text("fft2.panel.log_magnitude"))
        axes[2].imshow(result.shifted_phase, cmap="twilight", vmin=-3.14159, vmax=3.14159)
        axes[2].set_title(translator.text("fft2.panel.phase"))
        for axis in axes:
            axis.axis("off")
        fig.tight_layout()
        with tempfile.NamedTemporaryFile(
            prefix=".fft2.", suffix=".tmp", dir=path.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)
        fig.savefig(temporary, format="png", dpi=120)
        os.replace(temporary, path) if overwrite else os.link(temporary, path)
        return path
    finally:
        plt.close(fig)
        if temporary is not None and temporary.exists():
            temporary.unlink()
