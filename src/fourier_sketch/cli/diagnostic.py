"""Runnable diagnostic path from canonical Curve through Matplotlib output."""

import argparse
import locale as system_locale
import sys
from cmath import exp
from collections.abc import Sequence
from math import pi
from pathlib import Path

from fourier_sketch.application import EpicycleTimeline
from fourier_sketch.domain import Curve, DomainValidationError, Point2D, SpectrumOrdering
from fourier_sketch.math import fft_dft
from fourier_sketch.presentation import Translator, resolve_locale
from fourier_sketch.render import render_frame_png, run_interactive

DEFAULT_SAMPLE_COUNT = 128
DEFAULT_HARMONIC_COUNT = 15
DEFAULT_HEADLESS_FRAMES = 120


def main(argv: Sequence[str] | None = None) -> int:
    """Run a headless diagnostic or the temporary interactive Matplotlib surface."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    requested_locale = _requested_locale(arguments)
    os_hint = system_locale.getlocale()[0]
    translator = Translator(resolve_locale(requested_locale, os_hint=os_hint))
    parser = _parser(translator)
    options = parser.parse_args(arguments)

    try:
        timeline = _diagnostic_timeline(
            harmonic_count=options.harmonics,
            speed=options.speed,
        )
        if options.headless:
            if options.frames < 1 or options.frames >= 10_000:
                raise DomainValidationError("frames must be between 1 and 9999")
            timeline.play()
            frame = timeline.snapshot()
            for _ in range(options.frames):
                frame = timeline.advance(1.0 / 30.0)
            output = Path(options.output)
            render_frame_png(frame, output, translator)
            print(translator.text("cli.success", name=output.name))
        else:
            run_interactive(timeline, translator)
    except (DomainValidationError, FileExistsError, OSError) as error:
        if isinstance(error, FileExistsError):
            reason = translator.text("cli.output_exists", name=str(error))
        elif isinstance(error, DomainValidationError):
            reason = translator.text("cli.invalid_parameters")
        else:
            reason = translator.text("cli.io_failed")
        print(translator.text("cli.render_failed", reason=reason), file=sys.stderr)
        return 2
    return 0


def _diagnostic_timeline(*, harmonic_count: int, speed: float) -> EpicycleTimeline:
    values = tuple(
        exp(2j * pi * index / DEFAULT_SAMPLE_COUNT)
        + 0.35 * exp(-4j * pi * index / DEFAULT_SAMPLE_COUNT)
        + 0.15 * exp(6j * pi * index / DEFAULT_SAMPLE_COUNT)
        for index in range(DEFAULT_SAMPLE_COUNT)
    )
    curve = Curve(tuple(Point2D(value.real, value.imag) for value in values), closed=True)
    return EpicycleTimeline(
        fft_dft(values),
        curve,
        harmonic_count=harmonic_count,
        ordering=SpectrumOrdering.AMPLITUDE_DESCENDING,
        speed=speed,
    )


def _parser(translator: Translator) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=translator.text("cli.description"))
    parser.add_argument(
        "--headless",
        action="store_true",
        help=translator.text("cli.help.headless"),
    )
    parser.add_argument(
        "--output",
        default="epicycles.png",
        help=translator.text("cli.help.output"),
    )
    parser.add_argument(
        "--locale",
        default=None,
        help=translator.text("cli.help.locale"),
    )
    parser.add_argument(
        "--frames",
        type=int,
        default=DEFAULT_HEADLESS_FRAMES,
        help=translator.text("cli.help.frames"),
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help=translator.text("cli.help.speed"),
    )
    parser.add_argument(
        "--harmonics",
        type=int,
        default=DEFAULT_HARMONIC_COUNT,
        help=translator.text("cli.help.harmonics"),
    )
    return parser


def _requested_locale(arguments: list[str]) -> str | None:
    for index, value in enumerate(arguments):
        if value.startswith("--locale="):
            return value.partition("=")[2]
        if value == "--locale" and index + 1 < len(arguments):
            return arguments[index + 1]
    return None


if __name__ == "__main__":
    raise SystemExit(main())
