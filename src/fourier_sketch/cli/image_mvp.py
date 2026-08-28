"""Localized FS-013 image-to-epicycles MVP entry point."""

import argparse
import locale as system_locale
import sys
import unicodedata
from collections.abc import Sequence
from math import isfinite
from pathlib import Path
from typing import NoReturn

from fourier_sketch.application import (
    DEFAULT_CONTOUR_HARMONICS,
    DEFAULT_CONTOUR_SAMPLES,
    ImageContourTimelineResult,
    ImageMvpConfig,
    ImageMvpController,
    ImageMvpState,
    LocalPathError,
    validate_local_path,
    validate_timeline_speed,
)
from fourier_sketch.domain import DomainValidationError
from fourier_sketch.imaging import (
    BoundaryConnectivity,
    CannyParameters,
    DenoiseMode,
    EdgeAlgorithm,
    EdgeDetectionError,
    EdgeFailureCode,
    ImagePreprocessingOptions,
    ThresholdBoundaryParameters,
)
from fourier_sketch.presentation import Translator, resolve_locale
from fourier_sketch.render import render_image_mvp_png, run_image_mvp_interactive


class _ArgumentValidationError(ValueError):
    """Stable internal signal for localized argparse failures."""


class _LocalizedArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        _ = message
        raise _ArgumentValidationError


def main(argv: Sequence[str] | None = None) -> int:
    """Launch the UI or exercise the same image pipeline through a headless live path."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    requested_locale = _requested_locale(arguments)
    translator = Translator(resolve_locale(requested_locale, os_hint=system_locale.getlocale()[0]))
    try:
        options = _parser(translator).parse_args(arguments)
        config = _config(options)
        input_path = validate_local_path(Path(options.input), field_name="input")
        if not options.headless:
            run_image_mvp_interactive(input_path, translator, config=config)
            return 0

        _validate_headless_options(options.frames, options.frame_delta)
        output = validate_local_path(Path(options.output), field_name="output")
        controller = ImageMvpController()
        generation = controller.begin(config)
        snapshot = controller.process(generation, input_path)
        if snapshot.state is ImageMvpState.ERROR:
            assert snapshot.failure_key is not None
            _print_failure(translator, snapshot.failure_key)
            return 2
        if snapshot.state is ImageMvpState.CANCELLED:
            _print_failure(translator, "image_mvp.status.cancelled")
            return 2

        if snapshot.state is ImageMvpState.READY:
            controller.play()
            for _ in range(options.frames):
                snapshot = controller.tick(options.frame_delta)

        render_image_mvp_png(snapshot, output, translator, overwrite=options.overwrite)
        if snapshot.state is ImageMvpState.EMPTY:
            print(
                translator.text(
                    "cli.image_mvp_empty",
                    name=_safe_display_basename(output),
                )
            )
            return 0

        assert isinstance(snapshot.result, ImageContourTimelineResult)
        assert snapshot.frame is not None
        print(
            translator.text(
                "cli.image_mvp_success",
                name=_safe_display_basename(output),
                samples=snapshot.result.sampled_curve.sample_count,
                harmonics=snapshot.frame.selection.coefficient_count,
                trace=len(snapshot.frame.trace),
            )
        )
    except LocalPathError:
        _print_failure(translator, "image_mvp.error.local_path")
        return 2
    except (_ArgumentValidationError, DomainValidationError, EdgeDetectionError):
        _print_failure(translator, "image_mvp.error.validation")
        return 2
    except FileExistsError:
        _print_failure(translator, "cli.image_mvp_output_exists")
        return 2
    except OSError:
        _print_failure(translator, "cli.io_failed")
        return 2
    return 0


def _parser(translator: Translator) -> argparse.ArgumentParser:
    parser = _LocalizedArgumentParser(description=translator.text("cli.image_mvp_description"))
    parser.add_argument("input", help=translator.text("cli.help.image_input"))
    parser.add_argument(
        "--headless",
        action="store_true",
        help=translator.text("cli.help.headless"),
    )
    parser.add_argument(
        "--output",
        default="image-mvp.png",
        help=translator.text("cli.help.image_mvp_output"),
    )
    parser.add_argument(
        "--algorithm",
        choices=tuple(algorithm.value for algorithm in EdgeAlgorithm),
        default=EdgeAlgorithm.THRESHOLD_BOUNDARY.value,
        help=translator.text("cli.help.edge_algorithm"),
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=128,
        help=translator.text("cli.help.threshold"),
    )
    parser.add_argument(
        "--denoise",
        choices=tuple(mode.value for mode in DenoiseMode),
        default=DenoiseMode.NONE.value,
        help=translator.text("cli.help.denoise"),
    )
    parser.add_argument(
        "--autocontrast",
        action="store_true",
        help=translator.text("cli.help.autocontrast"),
    )
    parser.add_argument("--invert", action="store_true", help=translator.text("cli.help.invert"))
    parser.add_argument(
        "--connectivity",
        default=BoundaryConnectivity.EIGHT.value,
        help=translator.text("cli.help.edge_connectivity"),
    )
    parser.add_argument("--canny-low", default="100", help=translator.text("cli.help.canny_low"))
    parser.add_argument(
        "--canny-high",
        default="200",
        help=translator.text("cli.help.canny_high"),
    )
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
        "--samples",
        type=int,
        default=DEFAULT_CONTOUR_SAMPLES,
        help=translator.text("cli.help.samples"),
    )
    parser.add_argument(
        "--harmonics",
        type=int,
        default=DEFAULT_CONTOUR_HARMONICS,
        help=translator.text("cli.help.harmonics"),
    )
    parser.add_argument("--speed", type=float, default=1.0, help=translator.text("cli.help.speed"))
    parser.add_argument("--frames", type=int, default=60, help=translator.text("cli.help.frames"))
    parser.add_argument(
        "--frame-delta",
        type=float,
        default=1.0 / 60.0,
        help=translator.text("cli.help.frame_delta"),
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help=translator.text("cli.help.overwrite"),
    )
    parser.add_argument("--locale", default=None, help=translator.text("cli.help.locale"))
    return parser


def _config(options: argparse.Namespace) -> ImageMvpConfig:
    algorithm = EdgeAlgorithm(options.algorithm)
    boundary_parameters = ThresholdBoundaryParameters()
    canny_parameters = CannyParameters()
    if algorithm is EdgeAlgorithm.THRESHOLD_BOUNDARY:
        boundary_parameters = _boundary_parameters(options.connectivity)
    else:
        canny_parameters = _canny_parameters(
            options.canny_low,
            options.canny_high,
            options.canny_aperture,
            options.canny_gradient,
        )
    return ImageMvpConfig(
        preprocessing=ImagePreprocessingOptions(
            denoise=DenoiseMode(options.denoise),
            autocontrast=options.autocontrast,
            threshold=options.threshold,
            invert=options.invert,
        ),
        algorithm=algorithm,
        boundary_parameters=boundary_parameters,
        canny_parameters=canny_parameters,
        sample_count=options.samples,
        harmonic_count=options.harmonics,
        speed=options.speed,
    )


def _boundary_parameters(connectivity: str) -> ThresholdBoundaryParameters:
    try:
        parsed = BoundaryConnectivity(connectivity)
    except ValueError as error:
        raise EdgeDetectionError(
            EdgeFailureCode.INVALID_PARAMETERS,
            "boundary connectivity is invalid",
        ) from error
    return ThresholdBoundaryParameters(parsed)


def _canny_parameters(low: str, high: str, aperture: str, gradient: str) -> CannyParameters:
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


def _validate_headless_options(frames: int, frame_delta: float) -> None:
    if type(frames) is not int or not 1 <= frames <= 9_999:
        raise DomainValidationError("frames must be between 1 and 9999")
    if (
        isinstance(frame_delta, bool)
        or not isinstance(frame_delta, (int, float))
        or not isfinite(float(frame_delta))
        or frame_delta <= 0.0
    ):
        raise DomainValidationError("frame_delta must be positive and finite")
    validate_timeline_speed(1.0)


def _print_failure(translator: Translator, reason_key: str) -> None:
    print(
        translator.text("cli.image_mvp_failed", reason=translator.text(reason_key)),
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
    """Escape terminal controls in the only path-derived success field."""
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
            escaped.append(
                f"\\u{codepoint:04x}" if codepoint <= 0xFFFF else f"\\U{codepoint:08x}"
            )
        else:
            escaped.append(character)
    return "".join(escaped)


if __name__ == "__main__":
    raise SystemExit(main())
