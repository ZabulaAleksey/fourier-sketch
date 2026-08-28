"""Project threshold-boundary transform and explicit OpenCV Canny adapter."""

import importlib
import re
from typing import Protocol, cast

import numpy as np
from numpy.typing import NDArray

from .edge_model import (
    BoundaryConnectivity,
    CannyParameters,
    EdgeAlgorithm,
    EdgeDetectionError,
    EdgeDetectionResult,
    EdgeFailureCode,
    ThresholdBoundaryParameters,
)
from .model import RasterImage, RasterStage

_DEFAULT_BOUNDARY_PARAMETERS = ThresholdBoundaryParameters()
_DEFAULT_CANNY_PARAMETERS = CannyParameters()
_SAFE_BACKEND_VERSION = re.compile(r"[0-9A-Za-z][0-9A-Za-z._+-]{0,63}")


class _OpenCvBackend(Protocol):
    __version__: str

    def Canny(
        self,
        image: NDArray[np.uint8],
        threshold1: float,
        threshold2: float,
        *,
        apertureSize: int,
        L2gradient: bool,
    ) -> NDArray[np.uint8]: ...


def detect_threshold_boundary(
    source: RasterImage,
    parameters: ThresholdBoundaryParameters = _DEFAULT_BOUNDARY_PARAMETERS,
) -> EdgeDetectionResult:
    """Return foreground pixels adjacent to background/outside under 4/8-connectivity."""
    _validate_source(source, RasterStage.BINARY)
    if not isinstance(parameters, ThresholdBoundaryParameters):
        raise EdgeDetectionError(
            EdgeFailureCode.INVALID_PARAMETERS,
            "threshold boundary parameters are invalid",
        )
    foreground = np.frombuffer(source.pixels, dtype=np.uint8).reshape(
        source.height, source.width
    ) == np.uint8(255)
    interior = foreground.copy()
    interior[0, :] = False
    interior[-1, :] = False
    interior[:, 0] = False
    interior[:, -1] = False
    interior[1:, :] &= foreground[:-1, :]
    interior[:-1, :] &= foreground[1:, :]
    interior[:, 1:] &= foreground[:, :-1]
    interior[:, :-1] &= foreground[:, 1:]
    if parameters.connectivity is BoundaryConnectivity.EIGHT:
        interior[1:, 1:] &= foreground[:-1, :-1]
        interior[1:, :-1] &= foreground[:-1, 1:]
        interior[:-1, 1:] &= foreground[1:, :-1]
        interior[:-1, :-1] &= foreground[1:, 1:]
    edge_mask = foreground & ~interior
    edge_pixels = (edge_mask.astype(np.uint8) * np.uint8(255)).tobytes()
    return EdgeDetectionResult(
        edges=RasterImage(
            source.width,
            source.height,
            edge_pixels,
            RasterStage.BINARY,
        ),
        algorithm=EdgeAlgorithm.THRESHOLD_BOUNDARY,
        backend="fourier-sketch/numpy",
        parameters=parameters,
        source_stage=source.stage,
        source_dimensions=(source.width, source.height),
    )


def detect_canny_edges(
    source: RasterImage,
    parameters: CannyParameters = _DEFAULT_CANNY_PARAMETERS,
) -> EdgeDetectionResult:
    """Run the selected OpenCV Canny backend with no algorithm fallback."""
    _validate_source(source, RasterStage.GRAYSCALE)
    if not isinstance(parameters, CannyParameters):
        raise EdgeDetectionError(
            EdgeFailureCode.INVALID_PARAMETERS,
            "Canny parameters are invalid",
        )
    backend = _load_opencv_backend()
    source_array = np.frombuffer(source.pixels, dtype=np.uint8).reshape(source.height, source.width)
    try:
        output = backend.Canny(
            source_array,
            float(parameters.low_threshold),
            float(parameters.high_threshold),
            apertureSize=parameters.aperture_size,
            L2gradient=parameters.l2_gradient,
        )
    except Exception as error:
        raise EdgeDetectionError(
            EdgeFailureCode.BACKEND_FAILURE,
            "OpenCV Canny execution failed",
        ) from error
    if (
        not isinstance(output, np.ndarray)
        or output.dtype != np.uint8
        or output.shape != source_array.shape
    ):
        raise EdgeDetectionError(
            EdgeFailureCode.BACKEND_FAILURE,
            "OpenCV Canny returned an invalid raster",
        )
    try:
        edges = RasterImage(
            source.width,
            source.height,
            output.tobytes(),
            RasterStage.BINARY,
        )
    except ValueError as error:
        raise EdgeDetectionError(
            EdgeFailureCode.BACKEND_FAILURE,
            "OpenCV Canny returned non-binary pixels",
        ) from error
    return EdgeDetectionResult(
        edges=edges,
        algorithm=EdgeAlgorithm.CANNY,
        backend=f"opencv/{backend.__version__}",
        parameters=parameters,
        source_stage=source.stage,
        source_dimensions=(source.width, source.height),
    )


def _load_opencv_backend() -> _OpenCvBackend:
    try:
        module = importlib.import_module("cv2")
    except Exception as error:
        raise EdgeDetectionError(
            EdgeFailureCode.BACKEND_UNAVAILABLE,
            "OpenCV Canny backend is unavailable",
        ) from error
    version = getattr(module, "__version__", None)
    canny = getattr(module, "Canny", None)
    if (
        not isinstance(version, str)
        or _SAFE_BACKEND_VERSION.fullmatch(version) is None
        or not callable(canny)
    ):
        raise EdgeDetectionError(
            EdgeFailureCode.BACKEND_FAILURE,
            "OpenCV Canny backend contract is invalid",
        )
    return cast(_OpenCvBackend, module)


def _validate_source(source: RasterImage, expected_stage: RasterStage) -> None:
    if not isinstance(source, RasterImage) or source.stage is not expected_stage:
        raise EdgeDetectionError(
            EdgeFailureCode.INVALID_INPUT,
            f"edge algorithm requires {expected_stage.value} raster input",
        )
