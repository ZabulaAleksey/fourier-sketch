"""Interactive freehand diagnostic entry point."""

import argparse
import locale as system_locale
import sys
from collections.abc import Sequence
from typing import NoReturn

from fourier_sketch.domain import DomainValidationError
from fourier_sketch.math import ResamplingMethod
from fourier_sketch.presentation import Translator, resolve_locale
from fourier_sketch.render import run_freehand_interactive


class _ArgumentValidationError(ValueError):
    """Stable internal signal for localized argparse failures."""


class _LocalizedArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        _ = message
        raise _ArgumentValidationError


def main(argv: Sequence[str] | None = None) -> int:
    """Launch pointer capture backed by the actual Fourier/epicycle application path."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    requested_locale = _requested_locale(arguments)
    translator = Translator(resolve_locale(requested_locale, os_hint=system_locale.getlocale()[0]))
    try:
        options = _parser(translator).parse_args(arguments)
        run_freehand_interactive(
            translator,
            sample_count=options.samples,
            harmonic_count=options.harmonics,
            speed=options.speed,
            closed=options.closed,
            resampling_method=ResamplingMethod(options.resampling),
        )
    except (_ArgumentValidationError, DomainValidationError, OSError):
        print(
            translator.text(
                "cli.freehand_failed",
                reason=translator.text("cli.invalid_parameters"),
            ),
            file=sys.stderr,
        )
        return 2
    return 0


def _parser(translator: Translator) -> argparse.ArgumentParser:
    parser = _LocalizedArgumentParser(description=translator.text("cli.freehand_description"))
    parser.add_argument(
        "--samples", type=int, default=128, help=translator.text("cli.help.samples")
    )
    parser.add_argument(
        "--harmonics",
        type=int,
        default=None,
        help=translator.text("cli.help.harmonics"),
    )
    parser.add_argument("--speed", type=float, default=1.0, help=translator.text("cli.help.speed"))
    parser.add_argument("--closed", action="store_true", help=translator.text("cli.help.closed"))
    parser.add_argument(
        "--resampling",
        choices=tuple(method.value for method in ResamplingMethod),
        default=ResamplingMethod.UNIFORM_INDEX.value,
        help=translator.text("cli.help.resampling"),
    )
    parser.add_argument("--locale", default=None, help=translator.text("cli.help.locale"))
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
