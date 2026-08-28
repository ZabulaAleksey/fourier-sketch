"""Unit contracts for typed FS-011 edge values."""

import pytest

from fourier_sketch.domain import DomainValidationError
from fourier_sketch.imaging import (
    BoundaryConnectivity,
    CannyParameters,
    EdgeAlgorithm,
    EdgeDetectionError,
    EdgeDetectionResult,
    EdgeFailureCode,
    RasterImage,
    RasterStage,
    ThresholdBoundaryParameters,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("low", "high"),
    ((-1, 20), (20, 20), (21, 20), (0, 256), (True, 20), (0, False)),
)
def test_canny_thresholds_are_strictly_validated(low: object, high: object) -> None:
    with pytest.raises(EdgeDetectionError) as captured:
        CannyParameters(low_threshold=low, high_threshold=high)  # type: ignore[arg-type]

    assert captured.value.code is EdgeFailureCode.INVALID_PARAMETERS


@pytest.mark.parametrize("aperture", (0, 1, 9, 3.0, True))
def test_canny_aperture_accepts_only_supported_odd_sizes(aperture: object) -> None:
    with pytest.raises(EdgeDetectionError) as captured:
        CannyParameters(aperture_size=aperture)  # type: ignore[arg-type]

    assert captured.value.code is EdgeFailureCode.INVALID_PARAMETERS


def test_edge_parameter_enums_and_flags_are_explicit() -> None:
    with pytest.raises(EdgeDetectionError):
        ThresholdBoundaryParameters(connectivity="8")  # type: ignore[arg-type]
    with pytest.raises(EdgeDetectionError):
        CannyParameters(l2_gradient=1)  # type: ignore[arg-type]

    assert ThresholdBoundaryParameters(BoundaryConnectivity.FOUR).connectivity == "4"


def test_edge_result_records_coherent_nested_provenance() -> None:
    edges = RasterImage(2, 1, b"\x00\xff", RasterStage.BINARY)
    result = EdgeDetectionResult(
        edges,
        EdgeAlgorithm.CANNY,
        "opencv/test",
        CannyParameters(),
        RasterStage.GRAYSCALE,
        (2, 1),
    )

    assert result.edge_pixel_count == 1
    assert result.is_empty is False
    with pytest.raises(DomainValidationError, match="dimensions"):
        EdgeDetectionResult(
            edges,
            EdgeAlgorithm.CANNY,
            "opencv/test",
            CannyParameters(),
            RasterStage.GRAYSCALE,
            (1, 1),
        )
    with pytest.raises(DomainValidationError, match="threshold boundary parameters"):
        EdgeDetectionResult(
            edges,
            EdgeAlgorithm.THRESHOLD_BOUNDARY,
            "fourier-sketch/numpy",
            CannyParameters(),
            RasterStage.BINARY,
            (2, 1),
        )


def test_edge_result_rejects_spoofed_raster_and_stage() -> None:
    with pytest.raises(DomainValidationError, match="typed binary raster"):
        EdgeDetectionResult(
            object(),  # type: ignore[arg-type]
            EdgeAlgorithm.CANNY,
            "opencv/test",
            CannyParameters(),
            RasterStage.GRAYSCALE,
            (1, 1),
        )

    grayscale = RasterImage(1, 1, b"\x00", RasterStage.GRAYSCALE)
    with pytest.raises(DomainValidationError, match="typed binary raster"):
        EdgeDetectionResult(
            grayscale,
            EdgeAlgorithm.CANNY,
            "opencv/test",
            CannyParameters(),
            RasterStage.GRAYSCALE,
            (1, 1),
        )


@pytest.mark.parametrize(
    ("algorithm", "backend", "parameters", "stage"),
    (
        (
            EdgeAlgorithm.THRESHOLD_BOUNDARY,
            "opencv/5.0.0",
            ThresholdBoundaryParameters(),
            RasterStage.BINARY,
        ),
        (
            EdgeAlgorithm.CANNY,
            "opencv/\nspoof",
            CannyParameters(),
            RasterStage.GRAYSCALE,
        ),
        (
            EdgeAlgorithm.CANNY,
            f"opencv/{'x' * 65}",
            CannyParameters(),
            RasterStage.GRAYSCALE,
        ),
    ),
)
def test_edge_result_rejects_incoherent_or_unsafe_backend_provenance(
    algorithm: EdgeAlgorithm,
    backend: str,
    parameters: ThresholdBoundaryParameters | CannyParameters,
    stage: RasterStage,
) -> None:
    edges = RasterImage(1, 1, b"\x00", RasterStage.BINARY)

    with pytest.raises(DomainValidationError, match="backend provenance"):
        EdgeDetectionResult(edges, algorithm, backend, parameters, stage, (1, 1))
