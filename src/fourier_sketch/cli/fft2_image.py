"""Headless FS-020 local grayscale image Fourier diagnostic."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from fourier_sketch.application import (
    build_fft2_image,
    preprocess_local_image,
    safe_display_basename,
    validate_local_path,
)
from fourier_sketch.domain import DomainValidationError
from fourier_sketch.imaging import ImagePreprocessingOptions
from fourier_sketch.math import FFT2MaskPolicy, FourierBackendError
from fourier_sketch.presentation import Translator
from fourier_sketch.render import render_fft2_png


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="2D Fourier diagnostic for a local grayscale image"
    )
    parser.add_argument("input")
    parser.add_argument("--output", default="fft2.png")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--policy", choices=[p.value for p in FFT2MaskPolicy], default="none")
    parser.add_argument("--radius", type=float, default=None)
    parser.add_argument("--locale", default="en")
    options = parser.parse_args(argv)
    try:
        source = validate_local_path(Path(options.input), field_name="input")
        raster = preprocess_local_image(source, ImagePreprocessingOptions()).grayscale
        result = build_fft2_image(
            raster, policy=FFT2MaskPolicy(options.policy), radius=options.radius
        )
        render_fft2_png(
            result, Path(options.output), Translator(options.locale), overwrite=options.overwrite
        )
        print(
            f"2D Fourier diagnostic written: {safe_display_basename(Path(options.output))} "
            f"({result.width}x{result.height})"
        )
    except (DomainValidationError, FourierBackendError, FileExistsError, OSError) as error:
        print(f"2D Fourier diagnostic failed: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
