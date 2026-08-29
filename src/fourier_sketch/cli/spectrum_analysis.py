"""Deterministic measured discontinuity spectrum diagnostic."""

import argparse
from math import cos, pi, sin
from pathlib import Path

from fourier_sketch.application import (
    analyze_discontinuity_vs_continuous,
    build_discontinuous_fourier,
    compare_discontinuous_with_forced_route,
)
from fourier_sketch.domain import Curve, PiecewiseCurve, Point2D
from fourier_sketch.presentation import Translator
from fourier_sketch.render import render_spectrum_analysis_png


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="measured discontinuity spectrum diagnostic")
    parser.add_argument("--output", default="spectrum-analysis.png")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--locale", default="en")
    args = parser.parse_args(argv)
    circles = tuple(
        Curve(
            tuple(
                Point2D(cx + 0.35 * cos(2 * pi * index / 32), 0.35 * sin(2 * pi * index / 32))
                for index in range(32)
            ),
            closed=True,
        )
        for cx in (-0.6, 0.6)
    )
    result = build_discontinuous_fourier(PiecewiseCurve(circles), 128)
    forced = compare_discontinuous_with_forced_route(
        result,
        Curve(tuple(point for circle in circles for point in circle.points), closed=True),
    )
    analysis = analyze_discontinuity_vs_continuous(
        result, forced, (1, 2, 4, 8, 16, 32, 64, 128)
    )
    output = render_spectrum_analysis_png(
        analysis, Path(args.output), Translator(args.locale), overwrite=args.overwrite
    )
    print(
        f"spectrum analysis written: {output.name}; samples=128; "
        f"K=1..128; comparison=discontinuous_vs_continuous; measured_only=true"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
