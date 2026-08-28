"""Transactional application-state contracts for FS-014."""

from collections.abc import Callable
from pathlib import Path
from threading import Event, Thread

import pytest
from PIL import Image, ImageDraw

from fourier_sketch.application import (
    LocalPathError,
    SkeletonConfig,
    SkeletonController,
    SkeletonState,
    build_local_skeleton,
    export_local_skeleton,
)
from fourier_sketch.imaging import (
    ImagePreprocessingOptions,
    ImagePreprocessingResult,
    RasterImage,
    SkeletonAlgorithm,
    SkeletonizationResult,
    skeletonize_binary,
)

pytestmark = pytest.mark.unit


def _shape(path: Path) -> None:
    image = Image.new("L", (32, 24), 0)
    ImageDraw.Draw(image).rectangle((7, 5, 24, 18), fill=255)
    image.save(path)


def test_controller_publishes_complete_skeleton_result(tmp_path: Path) -> None:
    source = tmp_path / "shape.png"
    _shape(source)
    controller = SkeletonController()

    snapshot = controller.process(controller.begin(SkeletonConfig()), source)

    assert snapshot.state is SkeletonState.READY
    assert snapshot.result is not None
    assert snapshot.result.preprocessing.binary == snapshot.result.skeletonization.source
    assert snapshot.result.skeletonization.algorithm is SkeletonAlgorithm.LEE
    assert snapshot.result.skeletonization.backend.startswith("scikit-image/")


def test_blank_image_is_typed_empty_result(tmp_path: Path) -> None:
    source = tmp_path / "blank.png"
    Image.new("L", (12, 8), 0).save(source)
    controller = SkeletonController()

    snapshot = controller.process(controller.begin(SkeletonConfig()), source)

    assert snapshot.state is SkeletonState.EMPTY
    assert snapshot.result is not None
    assert snapshot.result.skeletonization.skeleton_pixel_count == 0


def test_cancelled_generation_never_publishes_late_skeleton(tmp_path: Path) -> None:
    source = tmp_path / "shape.png"
    _shape(source)
    started = Event()
    release = Event()

    def blocking_skeletonize(
        source: RasterImage,
        algorithm: SkeletonAlgorithm = SkeletonAlgorithm.LEE,
        *,
        cancellation_check: Callable[[], bool] | None = None,
    ) -> SkeletonizationResult:
        started.set()
        assert release.wait(timeout=5)
        return skeletonize_binary(source, algorithm, cancellation_check=cancellation_check)

    controller = SkeletonController(skeletonize=blocking_skeletonize)
    generation = controller.begin(SkeletonConfig())
    worker = Thread(target=controller.process, args=(generation, source))
    worker.start()
    assert started.wait(timeout=2)

    cancelled = controller.cancel()
    release.set()
    worker.join(timeout=5)

    assert not worker.is_alive()
    assert cancelled.state is SkeletonState.CANCELLED
    assert controller.snapshot().state is SkeletonState.CANCELLED
    assert controller.snapshot().result is None


def test_stale_generation_is_ignored_before_input_is_read() -> None:
    def unexpected_preprocess(
        _path: str | Path,
        _options: ImagePreprocessingOptions,
    ) -> ImagePreprocessingResult:
        raise AssertionError("stale generation must not read input")

    controller = SkeletonController(preprocess=unexpected_preprocess)
    stale = controller.begin(SkeletonConfig())
    current = controller.begin(SkeletonConfig())

    snapshot = controller.process(stale, Path("private.png"))

    assert snapshot.generation == current
    assert snapshot.state is SkeletonState.PROCESSING


def test_unexpected_boundary_failure_maps_to_safe_error_key() -> None:
    def failing_preprocess(
        _path: str | Path,
        _options: ImagePreprocessingOptions,
    ) -> ImagePreprocessingResult:
        raise RuntimeError("secret backend detail")

    controller = SkeletonController(preprocess=failing_preprocess)
    snapshot = controller.process(controller.begin(SkeletonConfig()), Path("private.png"))

    assert snapshot.state is SkeletonState.ERROR
    assert snapshot.failure_key == "skeleton.error.runtime"
    assert "secret" not in snapshot.failure_key


@pytest.mark.parametrize(
    "destination",
    (
        r"\\server\share\skeleton.png",
        r"\\?\C:\skeleton.png",
        r"C:relative.png",
        "NUL.png",
        "skeleton.png:stream",
    ),
)
def test_direct_export_rejects_network_device_and_ambiguous_paths(
    destination: str,
    tmp_path: Path,
) -> None:
    source = tmp_path / "shape.png"
    _shape(source)
    result = build_local_skeleton(source)

    with pytest.raises(LocalPathError):
        export_local_skeleton(result, destination)
