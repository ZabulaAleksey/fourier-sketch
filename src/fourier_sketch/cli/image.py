"""Localized diagnostic CLI for safe FS-010 image preprocessing."""

import argparse
import locale as system_locale
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import NoReturn

from fourier_sketch.application import export_preprocessing_result, preprocess_local_image
from fourier_sketch.imaging import (
    DenoiseMode,
    ImageFailureCode,
    ImageInputError,
    ImagePreprocessingOptions,
    RasterStage,
)
from fourier_sketch.presentation import Translator, resolve_locale


class _ArgumentValidationError(ValueError):
    """Stable internal signal for localized argparse failures."""


class _LocalizedArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        _ = message
        raise _ArgumentValidationError


def main(argv: Sequence[str] | None = None) -> int:
    """Run local file → validated intermediates → diagnostic PNG."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    requested_locale = _requested_locale(arguments)
    translator = Translator(resolve_locale(requested_locale, os_hint=system_locale.getlocale()[0]))
    try:
        options = _parser(translator).parse_args(arguments)
        preprocessing = ImagePreprocessingOptions(
            denoise=DenoiseMode(options.denoise),
            autocontrast=options.autocontrast,
            threshold=options.threshold,
            invert=options.invert,
        )
        result = preprocess_local_image(options.input, preprocessing)
        stage = RasterStage(options.stage)
        output = Path(options.output)
        export_preprocessing_result(result, stage, output, overwrite=options.overwrite)
        raster = result.grayscale if stage is RasterStage.GRAYSCALE else result.binary
        print(
            translator.text(
                "cli.image_success",
                name=output.name,
                format=result.provenance.decode.source_format.value,
                width=raster.width,
                height=raster.height,
                stage=stage.value,
            )
        )
    except _ArgumentValidationError:
        _print_failure(translator, ImageFailureCode.INVALID_OPTIONS)
        return 2
    except ImageInputError as error:
        _print_failure(translator, error.code)
        return 2
    except FileExistsError:
        print(
            translator.text("cli.image_failed", reason=translator.text("cli.image_output_exists")),
            file=sys.stderr,
        )
        return 2
    except OSError:
        print(
            translator.text("cli.image_failed", reason=translator.text("cli.io_failed")),
            file=sys.stderr,
        )
        return 2
    return 0


def _parser(translator: Translator) -> argparse.ArgumentParser:
    parser = _LocalizedArgumentParser(description=translator.text("cli.image_description"))
    parser.add_argument("input", help=translator.text("cli.help.image_input"))
    parser.add_argument(
        "--output", default="image-preprocessed.png", help=translator.text("cli.help.image_output")
    )
    parser.add_argument(
        "--stage",
        choices=tuple(stage.value for stage in RasterStage),
        default=RasterStage.BINARY.value,
        help=translator.text("cli.help.image_stage"),
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


def _print_failure(translator: Translator, code: ImageFailureCode) -> None:
    reason = translator.text(f"image.error.{code.value}")
    print(translator.text("cli.image_failed", reason=reason), file=sys.stderr)


def _requested_locale(arguments: list[str]) -> str | None:
    for index, value in enumerate(arguments):
        if value.startswith("--locale="):
            return value.partition("=")[2]
        if value == "--locale" and index + 1 < len(arguments):
            return arguments[index + 1]
    return None


if __name__ == "__main__":
    raise SystemExit(main())
