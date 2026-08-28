"""Contract tests for the lazy scikit-image skeleton adapter."""

import sys
import types
from collections.abc import Callable
from typing import Any

import numpy as np
import pytest

from fourier_sketch.domain import DomainValidationError
from fourier_sketch.imaging.model import RasterImage, RasterStage
from fourier_sketch.imaging.skeleton_model import (
    SkeletonAlgorithm,
    SkeletonFailureCode,
    SkeletonizationError,
    SkeletonizationResult,
)
from fourier_sketch.imaging.skimage_skeleton import skeletonize_binary


def raster(rows: list[str]) -> RasterImage:
    return RasterImage(
        len(rows[0]),
        len(rows),
        bytes(255 if c == "#" else 0 for row in rows for c in row),
        RasterStage.BINARY,
    )


def install_fake(
    monkeypatch: pytest.MonkeyPatch,
    fn: Callable[..., np.ndarray[Any, Any]],
    version: str = "0.26.0",
) -> None:
    skimage = types.ModuleType("skimage")
    skimage.__dict__["__version__"] = version
    morphology = types.ModuleType("skimage.morphology")
    morphology.__dict__["skeletonize"] = fn
    skimage.__dict__["morphology"] = morphology
    monkeypatch.setitem(sys.modules, "skimage", skimage)
    monkeypatch.setitem(sys.modules, "skimage.morphology", morphology)


def test_line_and_empty_properties(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake(values: np.ndarray, *, method: str) -> np.ndarray:
        assert method == "lee"
        return values.copy()

    install_fake(monkeypatch, fake)
    source = raster([".....", ".###.", "....."])
    result = skeletonize_binary(source)
    assert result.skeleton.width == 5 and result.skeleton.height == 3
    assert result.skeleton_pixel_count == 3
    assert result.source_foreground_pixels == 3
    assert not result.is_empty
    empty = skeletonize_binary(raster(["..."])).skeleton
    assert empty.pixels == b"\0\0\0"


@pytest.mark.parametrize(
    "shape",
    [
        [".....", ".###.", "..#..", "....."],
        [".....", "..#..", ".###.", "..#..", "....."],
        [".....", ".###.", ".#.#.", ".###.", "....."],
    ],
)
def test_topology_and_subset_properties(monkeypatch: pytest.MonkeyPatch, shape: list[str]) -> None:
    install_fake(monkeypatch, lambda values, *, method: values.copy())
    source = raster(shape)
    result = skeletonize_binary(source)
    assert result.skeleton.pixels == source.pixels
    assert all(value in (0, 255) for value in result.skeleton.pixels)


def test_input_is_immutable_and_backend_is_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def recording_fake(values: np.ndarray, *, method: str) -> np.ndarray:
        calls.append(method)
        return values.copy()

    install_fake(monkeypatch, recording_fake)
    source = raster(["###"])
    original = source.pixels
    result = skeletonize_binary(source)
    assert source.pixels == original
    assert result.backend == "scikit-image/0.26.0"
    assert calls == ["lee"]


def test_cancel_before_and_after(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake(monkeypatch, lambda values, *, method: values.copy())
    with pytest.raises(SkeletonizationError) as before:
        skeletonize_binary(raster(["#"]), cancellation_check=lambda: True)
    assert before.value.code is SkeletonFailureCode.CANCELLED
    checks = iter([False, False, True])
    with pytest.raises(SkeletonizationError) as after:
        skeletonize_binary(raster(["#"]), cancellation_check=lambda: next(checks))
    assert after.value.code is SkeletonFailureCode.CANCELLED


def test_foreground_budget_fails_before_backend_import(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "fourier_sketch.imaging.skimage_skeleton.MAX_SKELETON_FOREGROUND_PIXELS",
        1,
    )
    with pytest.raises(SkeletonizationError) as error:
        skeletonize_binary(raster(["##"]))
    assert error.value.code is SkeletonFailureCode.RESOURCE_LIMIT


def test_unavailable_backend_is_typed(monkeypatch: pytest.MonkeyPatch) -> None:
    original_import = __import__("importlib").import_module

    def unavailable(name: str) -> Any:
        if name.startswith("skimage"):
            raise OSError("native loader failed")
        return original_import(name)

    monkeypatch.setattr(
        "fourier_sketch.imaging.skimage_skeleton.importlib.import_module",
        unavailable,
    )
    with pytest.raises(SkeletonizationError) as error:
        skeletonize_binary(raster(["#"]))
    assert error.value.code is SkeletonFailureCode.BACKEND_UNAVAILABLE


@pytest.mark.parametrize(
    "bad",
    [
        lambda values, *, method: np.ones(values.shape, dtype=np.uint8),
        lambda values, *, method: np.ones((1, 1), dtype=bool),
        lambda values, *, method: np.logical_not(values),
    ],
)
def test_malformed_or_spoofed_output_rejected(
    monkeypatch: pytest.MonkeyPatch,
    bad: Callable[..., np.ndarray[Any, Any]],
) -> None:
    install_fake(monkeypatch, bad)
    with pytest.raises(SkeletonizationError) as error:
        skeletonize_binary(raster(["#."]))
    assert error.value.code is SkeletonFailureCode.MALFORMED_OUTPUT


def test_solid_two_by_two_backend_output_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake(monkeypatch, lambda values, *, method: values.copy())

    with pytest.raises(SkeletonizationError) as error:
        skeletonize_binary(raster(["##", "##"]))

    assert error.value.code is SkeletonFailureCode.MALFORMED_OUTPUT


def test_typed_result_rejects_solid_two_by_two_skeleton() -> None:
    thick = raster(["##", "##"])

    with pytest.raises(DomainValidationError, match="two-by-two"):
        SkeletonizationResult(
            thick,
            thick,
            SkeletonAlgorithm.LEE,
            "scikit-image/0.26.0",
            (2, 2),
            4,
            4,
        )


def test_backend_failure_has_no_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(values: np.ndarray, *, method: str) -> np.ndarray:
        raise RuntimeError("backend")

    install_fake(monkeypatch, fail)
    with pytest.raises(SkeletonizationError) as error:
        skeletonize_binary(raster(["#"]))
    assert error.value.code is SkeletonFailureCode.BACKEND_FAILURE
