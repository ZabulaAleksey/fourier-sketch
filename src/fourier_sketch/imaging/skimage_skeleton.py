"""Lazy, fail-closed scikit-image adapter for Lee skeletonization."""

import importlib
import re
from collections.abc import Callable

from .model import RasterImage, RasterStage
from .skeleton_model import (
    MAX_SKELETON_FOREGROUND_PIXELS,
    SkeletonAlgorithm,
    SkeletonFailureCode,
    SkeletonizationError,
    SkeletonizationResult,
)

_VERSION = re.compile(r"^0\.26\.\d+$")
CancellationCheck = Callable[[], bool]


def skeletonize_binary(
    source: RasterImage,
    algorithm: SkeletonAlgorithm = SkeletonAlgorithm.LEE,
    *,
    cancellation_check: CancellationCheck | None = None,
) -> SkeletonizationResult:
    """Return a provenance-bearing Lee skeleton; never silently substitutes a backend."""
    if algorithm is not SkeletonAlgorithm.LEE:
        raise SkeletonizationError(
            SkeletonFailureCode.INVALID_INPUT, "unsupported skeleton algorithm"
        )
    if not isinstance(source, RasterImage) or source.stage is not RasterStage.BINARY:
        raise SkeletonizationError(
            SkeletonFailureCode.INVALID_INPUT, "skeletonization requires a binary raster"
        )
    if _cancelled(cancellation_check):
        raise SkeletonizationError(SkeletonFailureCode.CANCELLED, "skeletonization was cancelled")
    foreground = source.pixels.count(255)
    if foreground > MAX_SKELETON_FOREGROUND_PIXELS:
        raise SkeletonizationError(
            SkeletonFailureCode.RESOURCE_LIMIT, "skeleton foreground exceeds the processing budget"
        )
    try:
        skimage = importlib.import_module("skimage")
        morphology = importlib.import_module("skimage.morphology")
        np = importlib.import_module("numpy")
    except Exception as exc:
        raise SkeletonizationError(
            SkeletonFailureCode.BACKEND_UNAVAILABLE, "scikit-image backend is unavailable"
        ) from exc
    version = getattr(skimage, "__version__", None)
    if not isinstance(version, str) or not _VERSION.fullmatch(version):
        raise SkeletonizationError(
            SkeletonFailureCode.BACKEND_UNAVAILABLE, "unsupported scikit-image backend version"
        )
    if _cancelled(cancellation_check):
        raise SkeletonizationError(SkeletonFailureCode.CANCELLED, "skeletonization was cancelled")
    try:
        values = (
            np.frombuffer(source.pixels, dtype=np.uint8).reshape((source.height, source.width))
            == 255
        )
        output = morphology.skeletonize(values, method="lee")
    except SkeletonizationError:
        raise
    except Exception as exc:
        raise SkeletonizationError(
            SkeletonFailureCode.BACKEND_FAILURE, "scikit-image skeletonization failed"
        ) from exc
    if _cancelled(cancellation_check):
        raise SkeletonizationError(SkeletonFailureCode.CANCELLED, "skeletonization was cancelled")
    if (
        not isinstance(output, np.ndarray)
        or output.shape != values.shape
        or output.dtype != np.dtype(bool)
    ):
        raise SkeletonizationError(
            SkeletonFailureCode.MALFORMED_OUTPUT, "scikit-image returned malformed skeleton output"
        )
    if not np.isfinite(output).all() or np.any(output & ~values):
        raise SkeletonizationError(
            SkeletonFailureCode.MALFORMED_OUTPUT, "scikit-image returned invalid skeleton semantics"
        )
    if output.shape[0] > 1 and output.shape[1] > 1:
        solid_two_by_two = output[:-1, :-1] & output[1:, :-1] & output[:-1, 1:] & output[1:, 1:]
        if np.any(solid_two_by_two):
            raise SkeletonizationError(
                SkeletonFailureCode.MALFORMED_OUTPUT,
                "scikit-image returned a non-thinned skeleton",
            )
    skeleton = RasterImage(
        source.width,
        source.height,
        np.where(output, 255, 0).astype(np.uint8).tobytes(),
        RasterStage.BINARY,
    )
    return SkeletonizationResult(
        source,
        skeleton,
        SkeletonAlgorithm.LEE,
        f"scikit-image/{version}",
        (source.width, source.height),
        foreground,
        int(output.sum()),
    )


def _cancelled(check: CancellationCheck | None) -> bool:
    if check is None:
        return False
    try:
        return check() is True
    except Exception as exc:
        raise SkeletonizationError(
            SkeletonFailureCode.CANCELLED, "skeleton cancellation check failed"
        ) from exc
