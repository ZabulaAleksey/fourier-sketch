"""Localized FS-014 skeleton preview/export entry point."""

import argparse
import locale as system_locale
import sys
import unicodedata
from collections.abc import Sequence
from pathlib import Path
from typing import NoReturn

from fourier_sketch.application import (
    LocalPathError,
    SkeletonConfig,
    SkeletonController,
    SkeletonState,
    export_local_skeleton,
    validate_local_path,
)
from fourier_sketch.domain import DomainValidationError
from fourier_sketch.imaging import DenoiseMode, ImagePreprocessingOptions
from fourier_sketch.presentation import Translator, resolve_locale
from fourier_sketch.render import render_skeleton_preview_png


class _ArgumentValidationError(ValueError):
    """Stable signal for localized argparse failures."""


class _LocalizedArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        _ = message
        raise _ArgumentValidationError


def main(argv: Sequence[str] | None = None) -> int:
    """Run local image -> binary preprocessing -> Lee skeleton -> one diagnostic PNG."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    requested_locale = _requested_locale(arguments)
    translator = Translator(resolve_locale(requested_locale, os_hint=system_locale.getlocale()[0]))
    try:
        options = _parser(translator).parse_args(arguments)
        config = SkeletonConfig(
            preprocessing=ImagePreprocessingOptions(
                denoise=DenoiseMode(options.denoise),
                autocontrast=options.autocontrast,
                threshold=options.threshold,
                invert=options.invert,
            )
        )
        input_path = validate_local_path(Path(options.input), field_name="input")
        output = validate_local_path(Path(options.output), field_name="output")
        controller = SkeletonController()
        snapshot = controller.process(controller.begin(config), input_path)
        if snapshot.state is SkeletonState.ERROR:
            assert snapshot.failure_key is not None
            _print_failure(translator, snapshot.failure_key)
            return 2
        if snapshot.state is SkeletonState.CANCELLED:
            _print_failure(translator, "skeleton.status.cancelled")
            return 2
        assert snapshot.result is not None
        if options.mode == "skeleton":
            export_local_skeleton(snapshot.result, output, overwrite=options.overwrite)
        else:
            render_skeleton_preview_png(
                snapshot.result,
                output,
                translator,
                overwrite=options.overwrite,
            )
        result = snapshot.result.skeletonization
        print(
            translator.text(
                "cli.skeleton_success",
                name=_safe_display_basename(output),
                mode=options.mode,
                algorithm=result.algorithm.value,
                backend=result.backend,
                width=result.skeleton.width,
                height=result.skeleton.height,
                source=result.source_foreground_pixels,
                skeleton=result.skeleton_pixel_count,
            )
        )
    except LocalPathError:
        _print_failure(translator, "skeleton.error.local_path")
        return 2
    except (_ArgumentValidationError, DomainValidationError):
        _print_failure(translator, "skeleton.error.validation")
        return 2
    except FileExistsError:
        _print_failure(translator, "cli.skeleton_output_exists")
        return 2
    except OSError:
        _print_failure(translator, "cli.io_failed")
        return 2
    return 0


def _parser(translator: Translator) -> argparse.ArgumentParser:
    parser = _LocalizedArgumentParser(description=translator.text("cli.skeleton_description"))
    parser.add_argument("input", help=translator.text("cli.help.image_input"))
    parser.add_argument(
        "--output",
        default="image-skeleton.png",
        help=translator.text("cli.help.skeleton_output"),
    )
    parser.add_argument(
        "--mode",
        choices=("skeleton", "preview"),
        default="skeleton",
        help=translator.text("cli.help.skeleton_mode"),
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
        "--overwrite", action="store_true", help=translator.text("cli.help.overwrite")
    )
    parser.add_argument("--locale", default=None, help=translator.text("cli.help.locale"))
    return parser


def _print_failure(translator: Translator, reason_key: str) -> None:
    print(
        translator.text("cli.skeleton_failed", reason=translator.text(reason_key)),
        file=sys.stderr,
    )


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
        category = unicodedata.category(character)
        if (
            not character.isprintable()
            or category in {"Cc", "Cf", "Cs"}
            or unicodedata.bidirectional(character) in dangerous_bidi
        ):
            codepoint = ord(character)
            escaped.append(f"\\u{codepoint:04x}" if codepoint <= 0xFFFF else f"\\U{codepoint:08x}")
        else:
            escaped.append(character)
    return "".join(escaped)


if __name__ == "__main__":
    raise SystemExit(main())
