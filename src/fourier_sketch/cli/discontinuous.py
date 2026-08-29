"""Deterministic two-circle discontinuous Fourier diagnostic."""

import argparse
from math import cos, pi, sin
from pathlib import Path

from fourier_sketch.application.discontinuous_fourier import (
    DiscontinuousMode,
    build_discontinuous_fourier,
)
from fourier_sketch.domain import Curve, PiecewiseCurve, Point2D
from fourier_sketch.math import PiecewiseAllocation
from fourier_sketch.presentation import Translator
from fourier_sketch.render import render_discontinuous_png


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="discontinuous Fourier diagnostic")
    parser.add_argument("--output", default="discontinuous.png")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--locale", default="en")
    parser.add_argument(
        "--mode",
        choices=tuple(mode.value for mode in DiscontinuousMode),
        default=DiscontinuousMode.PEN_UP_RENDERING.value,
    )
    args = parser.parse_args(argv)
    circles = tuple(
        Curve(
            tuple(
                Point2D(cx + 0.35 * cos(2 * pi * i / 32), 0.35 * sin(2 * pi * i / 32))
                for i in range(32)
            ),
            closed=True,
        )
        for cx in (-0.6, 0.6)
    )
    result = build_discontinuous_fourier(
        PiecewiseCurve(circles),
        128,
        allocation=PiecewiseAllocation.PROPORTIONAL,
        mode=DiscontinuousMode(args.mode),
    )
    render_discontinuous_png(
        result, Path(args.output), Translator(args.locale), overwrite=args.overwrite
    )
    print(
        "discontinuous diagnostic written: "
        f"{Path(args.output).name}; mode={result.mode.value}; "
        f"samples={result.spectrum.sample_count}; boundaries={len(result.boundaries)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
