"""Application-state contracts for the FS-013 image MVP."""

from pathlib import Path
from threading import Event, Thread

import pytest
from PIL import Image, ImageDraw

from fourier_sketch.application import (
    ImageContourTimelineResult,
    ImageMvpConfig,
    ImageMvpController,
    ImageMvpState,
    ImageNoContourResult,
    LocalPathError,
    preprocess_local_image,
    validate_local_path,
)
from fourier_sketch.domain import DomainValidationError
from fourier_sketch.imaging import ImagePreprocessingOptions, ImagePreprocessingResult

pytestmark = pytest.mark.unit


def _shape(path: Path) -> None:
    image = Image.new("L", (32, 24), 0)
    ImageDraw.Draw(image).rectangle((7, 5, 24, 18), fill=255)
    image.save(path)


def test_config_rejects_harmonics_outside_sample_budget() -> None:
    with pytest.raises(DomainValidationError, match="harmonic_count"):
        ImageMvpConfig(sample_count=8, harmonic_count=9)


def test_controller_publishes_complete_result_and_delegates_timeline(tmp_path: Path) -> None:
    source = tmp_path / "shape.png"
    _shape(source)
    controller = ImageMvpController()
    generation = controller.begin(ImageMvpConfig(sample_count=64, harmonic_count=9))

    processing = controller.snapshot()
    assert processing.state is ImageMvpState.PROCESSING
    assert processing.result is None
    ready = controller.process(generation, source)

    assert ready.state is ImageMvpState.READY
    assert isinstance(ready.result, ImageContourTimelineResult)
    assert ready.frame is not None
    assert ready.frame.trace[-1] == ready.frame.chain.endpoint
    assert ready.result.timeline.snapshot() == ready.frame

    controller.play()
    advanced = controller.tick(0.1)
    assert advanced.frame is not None
    assert len(advanced.frame.trace) == 2
    assert advanced.frame.trace[-1] == advanced.frame.chain.endpoint
    changed = controller.set_harmonic_count(5)
    assert changed.config.harmonic_count == 5
    assert changed.frame is not None and changed.frame.selection.coefficient_count == 5
    restarted = controller.restart()
    assert restarted.frame is not None and len(restarted.frame.trace) == 1


def test_blank_image_is_typed_empty_not_ready(tmp_path: Path) -> None:
    source = tmp_path / "blank.png"
    Image.new("L", (12, 8), 0).save(source)
    controller = ImageMvpController()

    snapshot = controller.process(controller.begin(ImageMvpConfig()), source)

    assert snapshot.state is ImageMvpState.EMPTY
    assert isinstance(snapshot.result, ImageNoContourResult)
    assert snapshot.frame is None


def test_corrupt_image_maps_to_safe_error_key(tmp_path: Path) -> None:
    source = tmp_path / "private-corrupt.png"
    source.write_bytes(b"not an image")
    controller = ImageMvpController()

    snapshot = controller.process(controller.begin(ImageMvpConfig()), source)

    assert snapshot.state is ImageMvpState.ERROR
    assert snapshot.failure_key == "image_mvp.error.image_input"
    assert str(source) not in snapshot.failure_key


def test_cancelled_generation_never_publishes_late_pipeline_result(tmp_path: Path) -> None:
    source = tmp_path / "shape.png"
    _shape(source)
    started = Event()
    release = Event()

    def blocking_preprocess(
        path: str | Path,
        options: ImagePreprocessingOptions,
    ) -> ImagePreprocessingResult:
        started.set()
        assert release.wait(timeout=5)
        return preprocess_local_image(path, options)

    controller = ImageMvpController(preprocess=blocking_preprocess)
    generation = controller.begin(ImageMvpConfig(sample_count=32, harmonic_count=8))
    worker = Thread(target=controller.process, args=(generation, source))
    worker.start()
    assert started.wait(timeout=2)

    cancelled = controller.cancel()
    release.set()
    worker.join(timeout=5)

    assert not worker.is_alive()
    assert cancelled.state is ImageMvpState.CANCELLED
    assert controller.snapshot().state is ImageMvpState.CANCELLED
    assert controller.snapshot().result is None


def test_stale_generation_is_ignored_before_untrusted_input_is_read() -> None:
    def unexpected_preprocess(
        _path: str | Path,
        _options: ImagePreprocessingOptions,
    ) -> ImagePreprocessingResult:
        raise AssertionError("stale generation must not read input")

    controller = ImageMvpController(preprocess=unexpected_preprocess)
    stale = controller.begin(ImageMvpConfig())
    current = controller.begin(ImageMvpConfig(sample_count=32, harmonic_count=8))

    snapshot = controller.process(stale, Path("private.png"))

    assert snapshot.generation == current
    assert snapshot.state is ImageMvpState.PROCESSING


def test_unexpected_boundary_failure_does_not_expose_exception_details() -> None:
    def failing_preprocess(
        _path: str | Path,
        _options: ImagePreprocessingOptions,
    ) -> ImagePreprocessingResult:
        raise RuntimeError("secret backend detail")

    controller = ImageMvpController(preprocess=failing_preprocess)
    snapshot = controller.process(controller.begin(ImageMvpConfig()), Path("private.png"))

    assert snapshot.state is ImageMvpState.ERROR
    assert snapshot.failure_key == "image_mvp.error.runtime"
    assert "secret" not in snapshot.failure_key


@pytest.mark.parametrize(
    "value",
    (
        r"\\server\share\image.png",
        r"\\?\C:\image.png",
        r"C:relative.png",
        "NUL.png",
        "image.png:stream",
    ),
)
def test_local_path_policy_rejects_network_device_and_ambiguous_names(value: str) -> None:
    with pytest.raises(LocalPathError):
        validate_local_path(Path(value), field_name="input")


def test_controller_rejects_unc_before_preprocessor_is_called() -> None:
    def unexpected_preprocess(
        _path: str | Path,
        _options: ImagePreprocessingOptions,
    ) -> ImagePreprocessingResult:
        raise AssertionError("UNC path must be rejected before filesystem access")

    controller = ImageMvpController(preprocess=unexpected_preprocess)
    snapshot = controller.process(
        controller.begin(ImageMvpConfig()),
        Path(r"\\server\share\private.png"),
    )

    assert snapshot.state is ImageMvpState.ERROR
    assert snapshot.failure_key == "image_mvp.error.local_path"
