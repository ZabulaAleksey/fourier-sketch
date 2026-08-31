"""Localized contour timeline diagnostic with opt-in FS-027 simplification comparison."""

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
    CurveSimplificationConfig,
    ImageNoContourResult,
    build_dominant_contour_timeline,
    compare_curve_simplification,
    preprocess_local_image,
    validate_timeline_speed,
)
from fourier_sketch.domain import DomainValidationError
from fourier_sketch.imaging import (
    BoundaryConnectivity,
    CannyParameters,
    ContourExtractionError,
    ContourFailureCode,
    DenoiseMode,
    EdgeAlgorithm,
    EdgeDetectionError,
    EdgeFailureCode,
    ImageFailureCode,
    ImageInputError,
    ImagePreprocessingOptions,
    ThresholdBoundaryParameters,
)
from fourier_sketch.math import (
    DEFAULT_SIMPLIFICATION_EVALUATIONS,
    CurveSimplificationError,
)
from fourier_sketch.presentation import Translator, resolve_locale
from fourier_sketch.render import render_curve_simplification_png, render_frame_png


class _ArgumentValidationError(ValueError):
    """Stable internal signal for localized argparse failures."""


class _LocalizedArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        _ = message
        raise _ArgumentValidationError


def main(argv: Sequence[str] | None = None) -> int:
    """Run the real image -> contour -> Fourier timeline -> diagnostic PNG path."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    requested_locale = _requested_locale(arguments)
    translator = Translator(resolve_locale(requested_locale, os_hint=system_locale.getlocale()[0]))
    try:
        options = _parser(translator).parse_args(arguments)
        algorithm = EdgeAlgorithm(options.algorithm)
        _validate_timeline_options(options.frames, options.frame_delta, options.speed)
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
        preprocessing = preprocess_local_image(
            options.input,
            ImagePreprocessingOptions(
                denoise=DenoiseMode(options.denoise),
                autocontrast=options.autocontrast,
                threshold=options.threshold,
                invert=options.invert,
            ),
        )
        result = build_dominant_contour_timeline(
            preprocessing,
            algorithm,
            sample_count=options.samples,
            harmonic_count=options.harmonics,
            speed=options.speed,
            boundary_parameters=boundary_parameters,
            canny_parameters=canny_parameters,
        )
        if isinstance(result, ImageNoContourResult):
            print(
                translator.text(
                    "cli.contour_empty",
                    algorithm=result.edges.algorithm.value,
                    backend=result.no_contour.extraction.backend,
                    reason=translator.text(f"contour.empty.{result.no_contour.reason.value}"),
                )
            )
            return 0

        if options.simplify_tolerance is not None:
            comparison = compare_curve_simplification(
                result.normalized.curve,
                CurveSimplificationConfig(
                    tolerance=options.simplify_tolerance,
                    sample_count=options.samples,
                    harmonic_count=options.harmonics,
                    speed=options.speed,
                    max_distance_evaluations=options.simplification_budget,
                ),
            )
            comparison.baseline_timeline.play()
            comparison.simplified_timeline.play()
            for _ in range(options.frames):
                comparison.baseline_timeline.advance(options.frame_delta)
                comparison.simplified_timeline.advance(options.frame_delta)
            output = Path(options.output)
            render_curve_simplification_png(
                comparison,
                output,
                translator,
                overwrite=options.overwrite,
            )
            metrics = comparison.simplification.metrics
            print(
                translator.text(
                    "cli.simplification_success",
                    name=_safe_display_basename(output),
                    algorithm=comparison.simplification.algorithm,
                    tolerance=comparison.simplification.tolerance,
                    source_points=metrics.source_point_count,
                    simplified_points=metrics.simplified_point_count,
                    maximum_deviation=metrics.maximum_segment_deviation,
                    sampled_rmse=comparison.sampled_metrics.rmse,
                    baseline_rmse=comparison.baseline_reconstruction_metrics.rmse,
                    simplified_rmse=comparison.simplified_reconstruction_metrics.rmse,
                    trace=len(comparison.baseline_timeline.snapshot().trace),
                )
            )
            return 0

        timeline = result.timeline
        timeline.play()
        frame = timeline.snapshot()
        for _ in range(options.frames):
            frame = timeline.advance(options.frame_delta)
        output = Path(options.output)
        render_frame_png(frame, output, translator, overwrite=options.overwrite)
        print(
            translator.text(
                "cli.contour_success",
                name=_safe_display_basename(output),
                algorithm=result.edges.algorithm.value,
                backend=result.normalized.provenance.extraction_backend,
                candidates=result.selection.extraction.candidate_count,
                points=result.normalized.curve.sample_count,
                samples=result.sampled_curve.sample_count,
                trace=len(frame.trace),
            )
        )
    except _ArgumentValidationError:
        _print_contour_failure(translator, ContourFailureCode.INVALID_INPUT)
        return 2
    except ImageInputError as error:
        _print_image_failure(translator, error.code)
        return 2
    except EdgeDetectionError as error:
        _print_edge_failure(translator, error.code)
        return 2
    except ContourExtractionError as error:
        _print_contour_failure(translator, error.code)
        return 2
    except CurveSimplificationError as error:
        print(
            translator.text(
                "cli.simplification_failed",
                reason=translator.text(f"simplification.error.{error.code.value}"),
            ),
            file=sys.stderr,
        )
        return 2
    except DomainValidationError:
        _print_contour_failure(translator, ContourFailureCode.INVALID_INPUT)
        return 2
    except FileExistsError:
        print(
            translator.text(
                "cli.contour_failed", reason=translator.text("cli.contour_output_exists")
            ),
            file=sys.stderr,
        )
        return 2
    except OSError:
        print(
            translator.text("cli.contour_failed", reason=translator.text("cli.io_failed")),
            file=sys.stderr,
        )
        return 2
    return 0


def _parser(translator: Translator) -> argparse.ArgumentParser:
    parser = _LocalizedArgumentParser(description=translator.text("cli.contour_description"))
    parser.add_argument("input", help=translator.text("cli.help.image_input"))
    parser.add_argument(
        "--output", default="contour-trace.png", help=translator.text("cli.help.contour_output")
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
        "--simplify-tolerance",
        type=float,
        default=None,
        help=translator.text("cli.help.simplify_tolerance"),
    )
    parser.add_argument(
        "--simplification-budget",
        type=int,
        default=DEFAULT_SIMPLIFICATION_EVALUATIONS,
        help=translator.text("cli.help.simplification_budget"),
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help=translator.text("cli.help.overwrite"),
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


def _validate_timeline_options(frames: int, frame_delta: float, speed: float) -> None:
    if type(frames) is not int or not 1 <= frames <= 9_999:
        raise DomainValidationError("frames must be between 1 and 9999")
    if (
        isinstance(frame_delta, bool)
        or not isinstance(frame_delta, (int, float))
        or not isfinite(float(frame_delta))
        or frame_delta <= 0.0
    ):
        raise DomainValidationError("frame_delta must be positive and finite")
    validate_timeline_speed(speed)


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


def _print_image_failure(translator: Translator, code: ImageFailureCode) -> None:
    print(
        translator.text(
            "cli.contour_failed", reason=translator.text(f"image.error.{code.value}")
        ),
        file=sys.stderr,
    )


def _print_edge_failure(translator: Translator, code: EdgeFailureCode) -> None:
    print(
        translator.text(
            "cli.contour_failed", reason=translator.text(f"edge.error.{code.value}")
        ),
        file=sys.stderr,
    )


def _print_contour_failure(translator: Translator, code: ContourFailureCode) -> None:
    print(
        translator.text(
            "cli.contour_failed", reason=translator.text(f"contour.error.{code.value}")
        ),
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
        if category in {"Cc", "Cf", "Cs"} or unicodedata.bidirectional(character) in dangerous_bidi:
            codepoint = ord(character)
            escaped.append(
                f"\\u{codepoint:04x}" if codepoint <= 0xFFFF else f"\\U{codepoint:08x}"
            )
        else:
            escaped.append(character)
    return "".join(escaped)


if __name__ == "__main__":
    raise SystemExit(main())
