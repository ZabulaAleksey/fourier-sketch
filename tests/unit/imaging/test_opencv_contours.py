"""FS-012 OpenCV contour adapter tests."""

from collections.abc import Sequence
from typing import Any

import numpy as np
import pytest
from numpy.typing import NDArray

from fourier_sketch.imaging import (
    MAX_CONTOUR_CANDIDATES,
    ContourExtractionError,
    ContourFailureCode,
    EdgeAlgorithm,
    EdgeDetectionResult,
    RasterImage,
    RasterStage,
    ThresholdBoundaryParameters,
    detect_threshold_boundary,
    extract_external_contours,
)

pytestmark = pytest.mark.unit


class _FakeBackend:
    __version__ = "5.0-test"
    RETR_EXTERNAL = 0
    CHAIN_APPROX_NONE = 1

    def __init__(self, contours: Sequence[NDArray[Any]]) -> None:
        self._contours = contours
        self.received_mode: int | None = None
        self.received_method: int | None = None

    def findContours(
        self,
        image: NDArray[np.uint8],
        mode: int,
        method: int,
    ) -> tuple[Sequence[NDArray[Any]], object]:
        assert image.dtype == np.uint8
        self.received_mode = mode
        self.received_method = method
        return self._contours, None


def _edge_result(width: int = 5, height: int = 5) -> Any:
    pixels = bytearray(width * height)
    for row in range(1, height - 1):
        for column in range(1, width - 1):
            pixels[row * width + column] = 255
    return detect_threshold_boundary(
        RasterImage(width, height, bytes(pixels), RasterStage.BINARY)
    )


def test_adapter_cleans_terminal_duplicate_and_ignores_zero_area_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    square = np.array(
        [[[1, 1]], [[2, 1]], [[3, 1]], [[3, 2]], [[3, 3]], [[2, 3]], [[1, 3]], [[1, 2]], [[1, 1]]],
        dtype=np.int32,
    )
    line = np.array([[[0, 0]], [[1, 0]], [[2, 0]], [[1, 0]]], dtype=np.int32)
    backend = _FakeBackend((line, square))
    monkeypatch.setattr(
        "fourier_sketch.imaging.opencv_contours._load_opencv_backend",
        lambda: backend,
    )

    result = extract_external_contours(_edge_result())

    assert result.backend == "opencv/5.0-test"
    assert result.retrieval_mode == "external"
    assert result.approximation_mode == "none"
    assert result.candidate_count == 1
    assert result.candidates[0].point_count == 8
    assert backend.received_mode == backend.RETR_EXTERNAL
    assert backend.received_method == backend.CHAIN_APPROX_NONE


@pytest.mark.parametrize(
    ("raw", "expected_code"),
    (
        (np.array([1, 2, 3], dtype=np.int32), ContourFailureCode.BACKEND_FAILURE),
        (
            np.array([[[0, 0]], [[2, 0]], [[2, 2]], [[0, 2]]], dtype=np.int32),
            ContourFailureCode.BACKEND_FAILURE,
        ),
        (
            np.array([[[0, 0]], [[1, 0]], [[1, 6]], [[0, 6]]], dtype=np.int32),
            ContourFailureCode.BACKEND_FAILURE,
        ),
    ),
)
def test_adapter_rejects_malformed_out_of_bounds_or_non_adjacent_backend_data(
    raw: NDArray[Any],
    expected_code: ContourFailureCode,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "fourier_sketch.imaging.opencv_contours._load_opencv_backend",
        lambda: _FakeBackend((raw,)),
    )

    with pytest.raises(ContourExtractionError) as captured:
        extract_external_contours(_edge_result())

    assert captured.value.code is expected_code


def test_real_empty_edge_map_returns_typed_empty_extraction() -> None:
    source = detect_threshold_boundary(
        RasterImage(4, 3, bytes(12), RasterStage.BINARY)
    )

    result = extract_external_contours(source)

    assert result.candidates == ()
    assert result.source.is_empty


def test_dense_edge_map_fails_before_loading_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    width = 1_001
    height = 1_000
    source = EdgeDetectionResult(
        edges=RasterImage(
            width,
            height,
            bytes([255]) * (width * height),
            RasterStage.BINARY,
        ),
        algorithm=EdgeAlgorithm.THRESHOLD_BOUNDARY,
        backend="fourier-sketch/numpy",
        parameters=ThresholdBoundaryParameters(),
        source_stage=RasterStage.BINARY,
        source_dimensions=(width, height),
    )
    monkeypatch.setattr(
        "fourier_sketch.imaging.opencv_contours._load_opencv_backend",
        lambda: pytest.fail("backend must not load after density preflight"),
    )

    with pytest.raises(ContourExtractionError) as captured:
        extract_external_contours(source)

    assert captured.value.code is ContourFailureCode.RESOURCE_LIMIT


def test_candidate_count_budget_is_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    square = np.array(
        [[[1, 1]], [[2, 1]], [[2, 2]], [[1, 2]]],
        dtype=np.int32,
    )
    backend = _FakeBackend((square,) * (MAX_CONTOUR_CANDIDATES + 1))
    monkeypatch.setattr(
        "fourier_sketch.imaging.opencv_contours._load_opencv_backend",
        lambda: backend,
    )

    with pytest.raises(ContourExtractionError) as captured:
        extract_external_contours(_edge_result())

    assert captured.value.code is ContourFailureCode.RESOURCE_LIMIT


def test_backend_import_failure_is_typed_without_native_detail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_import(name: str) -> None:
        assert name == "cv2"
        raise RuntimeError("sensitive native detail")

    monkeypatch.setattr(
        "fourier_sketch.imaging.opencv_contours.importlib.import_module",
        fail_import,
    )

    with pytest.raises(ContourExtractionError) as captured:
        extract_external_contours(_edge_result())

    assert captured.value.code is ContourFailureCode.BACKEND_UNAVAILABLE
    assert "sensitive native detail" not in str(captured.value)
