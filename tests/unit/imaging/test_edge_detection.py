"""Unit and negative contracts for FS-011 edge algorithms."""

from types import SimpleNamespace

import numpy as np
import pytest

from fourier_sketch.imaging import (
    BoundaryConnectivity,
    CannyParameters,
    EdgeAlgorithm,
    EdgeDetectionError,
    EdgeFailureCode,
    RasterImage,
    RasterStage,
    ThresholdBoundaryParameters,
    detect_canny_edges,
    detect_threshold_boundary,
)

pytestmark = pytest.mark.unit


def binary_raster(rows: tuple[tuple[int, ...], ...]) -> RasterImage:
    return RasterImage(
        len(rows[0]),
        len(rows),
        bytes(value for row in rows for value in row),
        RasterStage.BINARY,
    )


def test_threshold_boundary_treats_outside_as_background() -> None:
    source = binary_raster(((255, 255, 255), (255, 255, 255), (255, 255, 255)))

    result = detect_threshold_boundary(source)

    assert result.edges.pixels == bytes((255, 255, 255, 255, 0, 255, 255, 255, 255))
    assert result.edge_pixel_count == 8
    assert result.backend == "fourier-sketch/numpy"
    assert result.algorithm is EdgeAlgorithm.THRESHOLD_BOUNDARY


def test_threshold_boundary_connectivity_changes_diagonal_semantics() -> None:
    source = binary_raster(((0, 255, 255), (255, 255, 255), (255, 255, 255)))

    four = detect_threshold_boundary(source, ThresholdBoundaryParameters(BoundaryConnectivity.FOUR))
    eight = detect_threshold_boundary(
        source, ThresholdBoundaryParameters(BoundaryConnectivity.EIGHT)
    )

    assert four.edges.pixels[4] == 0
    assert eight.edges.pixels[4] == 255


def test_threshold_boundary_allows_an_empty_edge_map_without_mutating_source() -> None:
    source = binary_raster(((0, 0), (0, 0)))
    original = source.pixels

    result = detect_threshold_boundary(source)

    assert result.is_empty
    assert source.pixels == original


def test_edge_algorithms_reject_the_wrong_raster_stage() -> None:
    grayscale = RasterImage(1, 1, b"\x80", RasterStage.GRAYSCALE)
    binary = RasterImage(1, 1, b"\xff", RasterStage.BINARY)

    with pytest.raises(EdgeDetectionError) as threshold_error:
        detect_threshold_boundary(grayscale)
    with pytest.raises(EdgeDetectionError) as canny_error:
        detect_canny_edges(binary)

    assert threshold_error.value.code is EdgeFailureCode.INVALID_INPUT
    assert canny_error.value.code is EdgeFailureCode.INVALID_INPUT


def test_real_canny_returns_same_sized_binary_raster_without_source_mutation() -> None:
    pixels = np.zeros((16, 16), dtype=np.uint8)
    pixels[4:12, 4:12] = 255
    source = RasterImage(16, 16, pixels.tobytes(), RasterStage.GRAYSCALE)
    original = source.pixels

    result = detect_canny_edges(source, CannyParameters(50, 150, 3, True))

    assert result.algorithm is EdgeAlgorithm.CANNY
    assert result.backend.startswith("opencv/")
    assert result.edge_pixel_count > 0
    assert result.edges.stage is RasterStage.BINARY
    assert (result.edges.width, result.edges.height) == (16, 16)
    assert source.pixels == original


def test_missing_canny_backend_is_typed_and_never_falls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = RasterImage(2, 2, bytes((0, 255, 0, 255)), RasterStage.GRAYSCALE)
    binary = RasterImage(2, 2, bytes((0, 255, 0, 255)), RasterStage.BINARY)

    def unavailable(name: str) -> None:
        assert name == "cv2"
        raise ImportError("simulated unavailable backend")

    monkeypatch.setattr(
        "fourier_sketch.imaging.edge_detection.importlib.import_module", unavailable
    )

    with pytest.raises(EdgeDetectionError) as captured:
        detect_canny_edges(source)

    assert captured.value.code is EdgeFailureCode.BACKEND_UNAVAILABLE
    assert detect_threshold_boundary(binary).backend == "fourier-sketch/numpy"


def test_native_import_initialization_failure_is_typed_and_privacy_safe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = RasterImage(1, 1, b"\x00", RasterStage.GRAYSCALE)

    def fail_initialization(name: str) -> None:
        assert name == "cv2"
        raise RuntimeError("native init leaked detail")

    monkeypatch.setattr(
        "fourier_sketch.imaging.edge_detection.importlib.import_module",
        fail_initialization,
    )

    with pytest.raises(EdgeDetectionError) as captured:
        detect_canny_edges(source)

    assert captured.value.code is EdgeFailureCode.BACKEND_UNAVAILABLE
    assert "native init leaked detail" not in str(captured.value)


@pytest.mark.parametrize(
    "output",
    (
        None,
        np.zeros((1, 1), dtype=np.float32),
        np.array(((0, 1), (0, 0)), dtype=np.uint8),
    ),
)
def test_malformed_canny_output_is_a_typed_backend_failure(
    output: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = SimpleNamespace(__version__="test", Canny=lambda *args, **kwargs: output)
    monkeypatch.setattr(
        "fourier_sketch.imaging.edge_detection.importlib.import_module",
        lambda name: backend,
    )
    source = RasterImage(2, 2, bytes(4), RasterStage.GRAYSCALE)

    with pytest.raises(EdgeDetectionError) as captured:
        detect_canny_edges(source)

    assert captured.value.code is EdgeFailureCode.BACKEND_FAILURE


@pytest.mark.parametrize(
    "backend",
    (
        SimpleNamespace(__version__="test"),
        SimpleNamespace(__version__="", Canny=lambda *args, **kwargs: bytes(4)),
        SimpleNamespace(__version__="\nspoof", Canny=lambda *args, **kwargs: bytes(4)),
        SimpleNamespace(__version__="x" * 65, Canny=lambda *args, **kwargs: bytes(4)),
    ),
)
def test_invalid_canny_backend_contract_is_typed(
    backend: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "fourier_sketch.imaging.edge_detection.importlib.import_module",
        lambda name: backend,
    )
    source = RasterImage(2, 2, bytes(4), RasterStage.GRAYSCALE)

    with pytest.raises(EdgeDetectionError) as captured:
        detect_canny_edges(source)

    assert captured.value.code is EdgeFailureCode.BACKEND_FAILURE


def test_canny_backend_exception_is_typed(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        raise RuntimeError("backend detail")

    backend = SimpleNamespace(__version__="test", Canny=fail)
    monkeypatch.setattr(
        "fourier_sketch.imaging.edge_detection.importlib.import_module",
        lambda name: backend,
    )
    source = RasterImage(2, 2, bytes(4), RasterStage.GRAYSCALE)

    with pytest.raises(EdgeDetectionError) as captured:
        detect_canny_edges(source)

    assert captured.value.code is EdgeFailureCode.BACKEND_FAILURE
    assert "backend detail" not in str(captured.value)
