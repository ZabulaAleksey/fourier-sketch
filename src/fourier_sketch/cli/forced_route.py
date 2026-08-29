"""Localized FS-017 STRICT_SINGLE_CURVE diagnostic CLI."""

import argparse
import locale as system_locale
import sys
import unicodedata
from collections.abc import Sequence
from pathlib import Path
from typing import NoReturn

from fourier_sketch.application import build_local_forced_route
from fourier_sketch.domain import DomainValidationError
from fourier_sketch.imaging import DenoiseMode, ImageInputError, ImagePreprocessingOptions
from fourier_sketch.presentation import Translator, resolve_locale
from fourier_sketch.render import render_forced_route_overlay_png
from fourier_sketch.routing import ForcedRouteStatus


class _ArgumentValidationError(ValueError):
    pass


class _LocalizedArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        _ = message
        raise _ArgumentValidationError


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    translator = Translator(
        resolve_locale(_requested_locale(arguments), os_hint=system_locale.getlocale()[0])
    )
    try:
        options = _parser(translator).parse_args(arguments)
        result = build_local_forced_route(
            options.input,
            ImagePreprocessingOptions(
                denoise=DenoiseMode(options.denoise),
                autocontrast=options.autocontrast,
                threshold=options.threshold,
                invert=options.invert,
            ),
            sample_count=options.samples,
            harmonic_count=options.harmonics,
        )
        routing = result.routing
        if routing.status is not ForcedRouteStatus.READY:
            print(
                translator.text(
                    "cli.forced_route_empty",
                    status=routing.status.value,
                    reason=routing.reason or routing.status.value,
                )
            )
            return 0 if routing.status is ForcedRouteStatus.EMPTY else 2
        output = Path(options.output)
        render_forced_route_overlay_png(
            result, output, translator, overwrite=options.overwrite
        )
        assert routing.metrics is not None
        print(
            translator.text(
                "cli.forced_route_success",
                name=_safe_display_basename(output),
                original=routing.metrics.original_steps,
                duplicated=routing.metrics.duplicated_steps,
                bridges=routing.metrics.bridge_steps,
                added=routing.metrics.added_length,
            )
        )
        return 0
    except (ImageInputError, _ArgumentValidationError, DomainValidationError):
        print(
            translator.text(
                "cli.forced_route_failed",
                reason=translator.text("forced_route.error.validation"),
            ),
            file=sys.stderr,
        )
        return 2
    except FileExistsError:
        print(
            translator.text(
                "cli.forced_route_failed",
                reason=translator.text("cli.forced_route_output_exists"),
            ),
            file=sys.stderr,
        )
        return 2
    except OSError:
        print(
            translator.text("cli.forced_route_failed", reason=translator.text("cli.io_failed")),
            file=sys.stderr,
        )
        return 2


def _parser(translator: Translator) -> argparse.ArgumentParser:
    parser = _LocalizedArgumentParser(description=translator.text("cli.forced_route_description"))
    parser.add_argument("input", help=translator.text("cli.help.image_input"))
    parser.add_argument(
        "--output",
        default="forced-route.png",
        help=translator.text("cli.help.forced_route_output"),
    )
    parser.add_argument(
        "--threshold", type=int, default=128, help=translator.text("cli.help.threshold")
    )
    parser.add_argument(
        "--denoise",
        choices=tuple(mode.value for mode in DenoiseMode),
        default=DenoiseMode.NONE.value,
        help=translator.text("cli.help.denoise"),
    )
    parser.add_argument(
        "--autocontrast", action="store_true", help=translator.text("cli.help.autocontrast")
    )
    parser.add_argument("--invert", action="store_true", help=translator.text("cli.help.invert"))
    parser.add_argument(
        "--samples", type=int, default=256, help=translator.text("cli.help.samples")
    )
    parser.add_argument(
        "--harmonics", type=int, default=25, help=translator.text("cli.help.harmonics")
    )
    parser.add_argument(
        "--overwrite", action="store_true", help=translator.text("cli.help.overwrite")
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


def _safe_display_basename(path: Path) -> str:
    dangerous_bidi = frozenset({"BN", "LRE", "LRI", "LRO", "PDF", "PDI", "RLE", "RLI", "RLO"})
    escaped: list[str] = []
    for character in path.name:
        if (
            not character.isprintable()
            or unicodedata.category(character) in {"Cc", "Cf", "Cs"}
            or unicodedata.bidirectional(character) in dangerous_bidi
        ):
            codepoint = ord(character)
            escaped.append(
                f"\\u{codepoint:04x}" if codepoint <= 0xFFFF else f"\\U{codepoint:08x}"
            )
        else:
            escaped.append(character)
    return "".join(escaped)


if __name__ == "__main__":
    raise SystemExit(main())
