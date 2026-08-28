"""Fail-closed OpenCV external-contour extraction adapter."""

import importlib
import re
from collections.abc import Sequence
from typing import Any, Protocol, cast

import numpy as np
from numpy.typing import NDArray

from .contour_model import (
    MAX_CONTOUR_CANDIDATES,
    MAX_CONTOUR_EDGE_PIXELS,
    MAX_TOTAL_CONTOUR_POINTS,
    ContourCandidate,
    ContourExtractionError,
    ContourExtractionResult,
    ContourFailureCode,
    PixelPoint,
    contour_bounding_box,
    signed_shoelace_area2,
)
from .edge_model import EdgeDetectionResult

_SAFE_BACKEND_VERSION = re.compile(r"[0-9A-Za-z][0-9A-Za-z._+-]{0,63}")


class _OpenCvContourBackend(Protocol):
    __version__: str
    RETR_EXTERNAL: int
    CHAIN_APPROX_NONE: int

    def findContours(
        self,
        image: NDArray[np.uint8],
        mode: int,
        method: int,
    ) -> tuple[Sequence[NDArray[Any]], object]: ...


def extract_external_contours(source: EdgeDetectionResult) -> ContourExtractionResult:
    """Extract bounded external candidates without using backend order as semantics."""
    if not isinstance(source, EdgeDetectionResult):
        raise ContourExtractionError(
            ContourFailureCode.INVALID_INPUT,
            "contour extraction requires a typed edge result",
        )
    if source.edge_pixel_count > MAX_CONTOUR_EDGE_PIXELS:
        raise ContourExtractionError(
            ContourFailureCode.RESOURCE_LIMIT,
            "edge density exceeds the contour budget",
        )
    backend = _load_opencv_backend()
    raster = np.frombuffer(source.edges.pixels, dtype=np.uint8).reshape(
        source.edges.height, source.edges.width
    )
    try:
        output = backend.findContours(
            raster.copy(),
            backend.RETR_EXTERNAL,
            backend.CHAIN_APPROX_NONE,
        )
    except Exception as error:
        raise ContourExtractionError(
            ContourFailureCode.BACKEND_FAILURE,
            "OpenCV contour extraction failed",
        ) from error
    raw_contours = _validated_backend_output(output)
    raw_shapes = tuple(_validated_raw_shape(contour) for contour in raw_contours)
    total_raw_points = sum(shape[0] for shape in raw_shapes)
    if total_raw_points > MAX_TOTAL_CONTOUR_POINTS:
        raise ContourExtractionError(
            ContourFailureCode.RESOURCE_LIMIT,
            "contour points exceed the aggregate budget",
        )

    candidates: list[ContourCandidate] = []
    for raw in raw_contours:
        candidate = _candidate_from_backend(
            raw,
            source.source_dimensions,
            source.edges.pixels,
        )
        if candidate is not None:
            candidates.append(candidate)
    return ContourExtractionResult(
        candidates=tuple(candidates),
        source=source,
        backend=f"opencv/{backend.__version__}",
    )


def _load_opencv_backend() -> _OpenCvContourBackend:
    try:
        module = importlib.import_module("cv2")
    except Exception as error:
        raise ContourExtractionError(
            ContourFailureCode.BACKEND_UNAVAILABLE,
            "OpenCV contour backend is unavailable",
        ) from error
    version = getattr(module, "__version__", None)
    find_contours = getattr(module, "findContours", None)
    retrieval = getattr(module, "RETR_EXTERNAL", None)
    approximation = getattr(module, "CHAIN_APPROX_NONE", None)
    if (
        not isinstance(version, str)
        or _SAFE_BACKEND_VERSION.fullmatch(version) is None
        or not callable(find_contours)
        or type(retrieval) is not int
        or type(approximation) is not int
    ):
        raise ContourExtractionError(
            ContourFailureCode.BACKEND_FAILURE,
            "OpenCV contour backend contract is invalid",
        )
    return cast(_OpenCvContourBackend, module)


def _validated_backend_output(output: object) -> Sequence[NDArray[Any]]:
    if not isinstance(output, tuple) or len(output) != 2:
        raise ContourExtractionError(
            ContourFailureCode.BACKEND_FAILURE,
            "OpenCV contour backend returned an invalid result",
        )
    contours = output[0]
    if not isinstance(contours, (tuple, list)):
        raise ContourExtractionError(
            ContourFailureCode.BACKEND_FAILURE,
            "OpenCV contour backend returned invalid candidates",
        )
    if len(contours) > MAX_CONTOUR_CANDIDATES:
        raise ContourExtractionError(
            ContourFailureCode.RESOURCE_LIMIT,
            "contour candidate count exceeds the budget",
        )
    return contours


def _validated_raw_shape(raw: object) -> tuple[int, ...]:
    if (
        not isinstance(raw, np.ndarray)
        or raw.dtype == np.bool_
        or not np.issubdtype(raw.dtype, np.integer)
        or raw.ndim not in (2, 3)
        or (raw.ndim == 2 and raw.shape[1:] != (2,))
        or (raw.ndim == 3 and raw.shape[1:] != (1, 2))
    ):
        raise ContourExtractionError(
            ContourFailureCode.BACKEND_FAILURE,
            "OpenCV contour backend returned a malformed candidate",
        )
    return tuple(int(component) for component in raw.shape)


def _candidate_from_backend(
    raw: NDArray[Any],
    source_dimensions: tuple[int, int],
    source_pixels: bytes,
) -> ContourCandidate | None:
    _validated_raw_shape(raw)
    width, height = source_dimensions
    flattened = raw.reshape((-1, 2))
    points: list[PixelPoint] = []
    for column_value, row_value in flattened:
        column = int(column_value)
        row = int(row_value)
        if not 0 <= column < width or not 0 <= row < height:
            raise ContourExtractionError(
                ContourFailureCode.BACKEND_FAILURE,
                "OpenCV contour candidate lies outside the source raster",
            )
        if source_pixels[row * width + column] != 255:
            raise ContourExtractionError(
                ContourFailureCode.BACKEND_FAILURE,
                "OpenCV contour candidate does not reference an edge pixel",
            )
        point = PixelPoint(column=column, row=row)
        if not points or point != points[-1]:
            points.append(point)
    if len(points) > 1 and points[-1] == points[0]:
        points.pop()
    if len(points) < 3 or len(set(points)) != len(points):
        return None
    sequence = tuple(points)
    _validate_chain_adjacency(sequence)
    area2 = signed_shoelace_area2(sequence)
    if area2 == 0:
        return None
    return ContourCandidate(
        points=sequence,
        signed_area2=area2,
        bounding_box=contour_bounding_box(sequence),
    )


def _validate_chain_adjacency(points: tuple[PixelPoint, ...]) -> None:
    pairs = zip(points, (*points[1:], points[0]), strict=True)
    if any(
        max(abs(left.column - right.column), abs(left.row - right.row)) > 1
        for left, right in pairs
    ):
        raise ContourExtractionError(
            ContourFailureCode.BACKEND_FAILURE,
            "OpenCV CHAIN_APPROX_NONE adjacency contract was violated",
        )
