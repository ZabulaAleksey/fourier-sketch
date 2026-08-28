"""Localized FS-011 CLI for explicit edge-intermediate selection."""

import argparse
import locale as system_locale
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import NoReturn

from fourier_sketch.application import (
    detect_preprocessed_edges,
    export_edge_result,
    preprocess_local_image,
)
from fourier_sketch.imaging import (
    BoundaryConnectivity,
    CannyParameters,
    DenoiseMode,
    EdgeAlgorithm,
    EdgeDetectionError,
    EdgeFailureCode,
    ImageFailureCode,
    ImageInputError,
    ImagePreprocessingOptions,
    ThresholdBoundaryParameters,
)
from fourier_sketch.presentation import Translator, resolve_locale


class _ArgumentValidationError(ValueError):
    """Stable internal signal for localized argparse failures."""


class _LocalizedArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        _ = message
        raise _ArgumentValidationError


def main(argv: Sequence[str] | None = None) -> int:
    """Run local image -> preprocessing -> selected edge map -> diagnostic PNG."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    requested_locale = _requested_locale(arguments)
    translator = Translator(resolve_locale(requested_locale, os_hint=system_locale.getlocale()[0]))
    try:
        options = _parser(translator).parse_args(arguments)
        preprocessing = preprocess_local_image(
            options.input,
            ImagePreprocessingOptions(
                denoise=DenoiseMode(options.denoise),
                autocontrast=options.autocontrast,
                threshold=options.threshold,
                invert=options.invert,
            ),
        )
        algorithm = EdgeAlgorithm(options.algorithm)
        if algorithm is EdgeAlgorithm.THRESHOLD_BOUNDARY:
            result = detect_preprocessed_edges(
                preprocessing,
                algorithm,
                boundary_parameters=_boundary_parameters(options.connectivity),
            )
        else:
            result = detect_preprocessed_edges(
                preprocessing,
                algorithm,
                canny_parameters=_canny_parameters(
                    options.canny_low,
                    options.canny_high,
                    options.canny_aperture,
                    options.canny_gradient,
                ),
            )
        output = Path(options.output)
        export_edge_result(result, output, overwrite=options.overwrite)
        print(
            translator.text(
                "cli.edge_success",
                name=output.name,
                algorithm=result.algorithm.value,
                backend=result.backend,
                width=result.edges.width,
                height=result.edges.height,
                count=result.edge_pixel_count,
            )
        )
    except _ArgumentValidationError:
        _print_edge_failure(translator, EdgeFailureCode.INVALID_PARAMETERS)
        return 2
    except ImageInputError as error:
        _print_image_failure(translator, error.code)
        return 2
    except EdgeDetectionError as error:
        _print_edge_failure(translator, error.code)
        return 2
    except FileExistsError:
        print(
            translator.text("cli.edge_failed", reason=translator.text("cli.edge_output_exists")),
            file=sys.stderr,
        )
        return 2
    except OSError:
        print(
            translator.text("cli.edge_failed", reason=translator.text("cli.io_failed")),
            file=sys.stderr,
        )
        return 2
    return 0


def _parser(translator: Translator) -> argparse.ArgumentParser:
    parser = _LocalizedArgumentParser(description=translator.text("cli.edge_description"))
    parser.add_argument("input", help=translator.text("cli.help.image_input"))
    parser.add_argument(
        "--output", default="image-edges.png", help=translator.text("cli.help.edge_output")
    )
    parser.add_argument(
        "--algorithm",
        choices=tuple(algorithm.value for algorithm in EdgeAlgorithm),
        default=EdgeAlgorithm.THRESHOLD_BOUNDARY.value,
        help=translator.text("cli.help.edge_algorithm"),
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
        "--connectivity",
        default=BoundaryConnectivity.EIGHT.value,
        help=translator.text("cli.help.edge_connectivity"),
    )
    parser.add_argument("--canny-low", default="100", help=translator.text("cli.help.canny_low"))
    parser.add_argument("--canny-high", default="200", help=translator.text("cli.help.canny_high"))
    parser.add_argument(
        "--canny-aperture",
        default="3",
        help=translator.text("cli.help.canny_aperture"),
    )
    parser.add_argument(
        "--canny-gradient",
        default="l2",
        help=translator.text("cli.help.canny_gradient"),
    )
    parser.add_argument(
        "--overwrite", action="store_true", help=translator.text("cli.help.overwrite")
    )
    parser.add_argument("--locale", default=None, help=translator.text("cli.help.locale"))
    return parser


def _boundary_parameters(connectivity: str) -> ThresholdBoundaryParameters:
    try:
        parsed = BoundaryConnectivity(connectivity)
    except ValueError as error:
        raise EdgeDetectionError(
            EdgeFailureCode.INVALID_PARAMETERS,
            "boundary connectivity is invalid",
        ) from error
    return ThresholdBoundaryParameters(parsed)


def _canny_parameters(
    low: str,
    high: str,
    aperture: str,
    gradient: str,
) -> CannyParameters:
    if gradient not in ("l1", "l2"):
        raise EdgeDetectionError(
            EdgeFailureCode.INVALID_PARAMETERS,
            "Canny gradient norm is invalid",
        )
    try:
        low_threshold = int(low)
        high_threshold = int(high)
        aperture_size = int(aperture)
    except ValueError as error:
        raise EdgeDetectionError(
            EdgeFailureCode.INVALID_PARAMETERS,
            "Canny numeric parameters are invalid",
        ) from error
    return CannyParameters(
        low_threshold=low_threshold,
        high_threshold=high_threshold,
        aperture_size=aperture_size,
        l2_gradient=gradient == "l2",
    )


def _print_image_failure(translator: Translator, code: ImageFailureCode) -> None:
    reason = translator.text(f"image.error.{code.value}")
    print(translator.text("cli.edge_failed", reason=reason), file=sys.stderr)


def _print_edge_failure(translator: Translator, code: EdgeFailureCode) -> None:
    reason = translator.text(f"edge.error.{code.value}")
    print(translator.text("cli.edge_failed", reason=reason), file=sys.stderr)


def _requested_locale(arguments: list[str]) -> str | None:
    for index, value in enumerate(arguments):
        if value.startswith("--locale="):
            return value.partition("=")[2]
        if value == "--locale" and index + 1 < len(arguments):
            return arguments[index + 1]
    return None


if __name__ == "__main__":
    raise SystemExit(main())
