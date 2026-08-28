"""Application selection for explicitly different FS-011 edge algorithms."""

from pathlib import Path

from fourier_sketch.domain import DomainValidationError
from fourier_sketch.imaging import (
    CannyParameters,
    EdgeAlgorithm,
    EdgeDetectionResult,
    ImagePreprocessingResult,
    ThresholdBoundaryParameters,
    detect_canny_edges,
    detect_threshold_boundary,
    export_raster_png,
)

_DEFAULT_BOUNDARY_PARAMETERS = ThresholdBoundaryParameters()
_DEFAULT_CANNY_PARAMETERS = CannyParameters()


def detect_preprocessed_edges(
    source: ImagePreprocessingResult,
    algorithm: EdgeAlgorithm,
    *,
    boundary_parameters: ThresholdBoundaryParameters = _DEFAULT_BOUNDARY_PARAMETERS,
    canny_parameters: CannyParameters = _DEFAULT_CANNY_PARAMETERS,
) -> EdgeDetectionResult:
    """Dispatch one selected edge algorithm without substituting the other."""
    if not isinstance(source, ImagePreprocessingResult):
        raise DomainValidationError("edge detection requires a preprocessing result")
    if not isinstance(algorithm, EdgeAlgorithm):
        raise DomainValidationError("edge algorithm must be explicit")
    if algorithm is EdgeAlgorithm.THRESHOLD_BOUNDARY:
        return detect_threshold_boundary(source.binary, boundary_parameters)
    return detect_canny_edges(source.grayscale, canny_parameters)


def export_edge_result(
    result: EdgeDetectionResult,
    destination: str | Path,
    *,
    overwrite: bool = False,
) -> None:
    """Publish only the selected binary edge intermediate as diagnostic PNG."""
    if not isinstance(result, EdgeDetectionResult):
        raise DomainValidationError("edge export requires an edge result")
    export_raster_png(result.edges, destination, overwrite=overwrite)
