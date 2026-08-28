"""Transactional application state for the FS-013 image-to-epicycles MVP."""

from collections.abc import Callable
from dataclasses import dataclass, field, replace
from enum import StrEnum
from pathlib import Path
from threading import Event, Lock
from typing import Protocol

from fourier_sketch.application.diagnostic_epicycles import (
    EpicycleFrame,
    validate_timeline_speed,
)
from fourier_sketch.application.dominant_contour import (
    DEFAULT_CONTOUR_HARMONICS,
    DEFAULT_CONTOUR_SAMPLES,
    ImageContourTimelineResult,
    ImageNoContourResult,
    build_dominant_contour_timeline,
)
from fourier_sketch.application.image_preprocessing import preprocess_local_image
from fourier_sketch.domain import DomainValidationError
from fourier_sketch.imaging import (
    CannyParameters,
    ContourExtractionError,
    EdgeAlgorithm,
    EdgeDetectionError,
    ImageInputError,
    ImagePreprocessingOptions,
    ImagePreprocessingResult,
    ThresholdBoundaryParameters,
)

from .local_paths import LocalPathError, validate_local_path


class ImageMvpState(StrEnum):
    """Observable states of the single-image workflow."""

    INITIAL = "initial"
    PROCESSING = "processing"
    READY = "ready"
    EMPTY = "empty"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class ImageMvpConfig:
    """Bounded, explicit choices for one image-processing generation."""

    preprocessing: ImagePreprocessingOptions = field(default_factory=ImagePreprocessingOptions)
    algorithm: EdgeAlgorithm = EdgeAlgorithm.THRESHOLD_BOUNDARY
    boundary_parameters: ThresholdBoundaryParameters = field(
        default_factory=ThresholdBoundaryParameters
    )
    canny_parameters: CannyParameters = field(default_factory=CannyParameters)
    sample_count: int = DEFAULT_CONTOUR_SAMPLES
    harmonic_count: int = DEFAULT_CONTOUR_HARMONICS
    speed: float = 1.0

    def __post_init__(self) -> None:
        if not isinstance(self.preprocessing, ImagePreprocessingOptions):
            raise DomainValidationError("image MVP requires preprocessing options")
        if not isinstance(self.algorithm, EdgeAlgorithm):
            raise DomainValidationError("image MVP requires an explicit edge algorithm")
        if not isinstance(self.boundary_parameters, ThresholdBoundaryParameters):
            raise DomainValidationError("image MVP requires boundary parameters")
        if not isinstance(self.canny_parameters, CannyParameters):
            raise DomainValidationError("image MVP requires Canny parameters")
        if type(self.sample_count) is not int or not 3 <= self.sample_count <= 4096:
            raise DomainValidationError("image MVP sample_count must be between 3 and 4096")
        if (
            type(self.harmonic_count) is not int
            or not 1 <= self.harmonic_count <= self.sample_count
        ):
            raise DomainValidationError(
                "image MVP harmonic_count must be between 1 and sample_count"
            )
        object.__setattr__(self, "speed", validate_timeline_speed(self.speed))


ImageMvpResult = ImageContourTimelineResult | ImageNoContourResult


@dataclass(frozen=True, slots=True)
class ImageMvpSnapshot:
    """Immutable publish point; partial pipeline values are never observable as ready."""

    generation: int
    state: ImageMvpState
    config: ImageMvpConfig
    result: ImageMvpResult | None = None
    frame: EpicycleFrame | None = None
    failure_key: str | None = None

    def __post_init__(self) -> None:
        if type(self.generation) is not int or self.generation < 0:
            raise DomainValidationError("image MVP generation must be a non-negative integer")
        if not isinstance(self.state, ImageMvpState) or not isinstance(
            self.config, ImageMvpConfig
        ):
            raise DomainValidationError("image MVP snapshot requires typed state and config")

        if self.state is ImageMvpState.READY:
            if not isinstance(self.result, ImageContourTimelineResult) or not isinstance(
                self.frame, EpicycleFrame
            ):
                raise DomainValidationError("ready image MVP requires a timeline result and frame")
            if self.frame != self.result.timeline.snapshot() or self.failure_key is not None:
                raise DomainValidationError("ready image MVP snapshot is inconsistent")
            return

        if self.state is ImageMvpState.EMPTY:
            if (
                not isinstance(self.result, ImageNoContourResult)
                or self.frame is not None
                or self.failure_key is not None
            ):
                raise DomainValidationError("empty image MVP requires only a no-contour result")
            return

        if self.state is ImageMvpState.ERROR:
            if (
                self.result is not None
                or self.frame is not None
                or not isinstance(self.failure_key, str)
                or not self.failure_key
            ):
                raise DomainValidationError("failed image MVP requires only a failure resource key")
            return

        if self.result is not None or self.frame is not None or self.failure_key is not None:
            raise DomainValidationError(
                "non-terminal image MVP states cannot expose partial results"
            )


_PreprocessImage = Callable[
    [str | Path, ImagePreprocessingOptions],
    ImagePreprocessingResult,
]


class _BuildTimeline(Protocol):
    def __call__(
        self,
        preprocessing: ImagePreprocessingResult,
        algorithm: EdgeAlgorithm,
        *,
        sample_count: int,
        harmonic_count: int,
        speed: float,
        boundary_parameters: ThresholdBoundaryParameters,
        canny_parameters: CannyParameters,
    ) -> ImageMvpResult: ...


class ImageMvpController:
    """Own the shared image pipeline and publish generation-safe UI state."""

    def __init__(
        self,
        *,
        preprocess: _PreprocessImage = preprocess_local_image,
        build_timeline: _BuildTimeline = build_dominant_contour_timeline,
    ) -> None:
        self._preprocess = preprocess
        self._build_timeline = build_timeline
        self._lock = Lock()
        self._generation = 0
        self._cancel_event = Event()
        self._snapshot = ImageMvpSnapshot(
            generation=0,
            state=ImageMvpState.INITIAL,
            config=ImageMvpConfig(),
        )

    def snapshot(self) -> ImageMvpSnapshot:
        with self._lock:
            return self._snapshot

    def begin(self, config: ImageMvpConfig) -> int:
        if not isinstance(config, ImageMvpConfig):
            raise DomainValidationError("image MVP processing requires a typed config")
        with self._lock:
            self._cancel_event.set()
            self._generation += 1
            self._cancel_event = Event()
            self._snapshot = ImageMvpSnapshot(
                generation=self._generation,
                state=ImageMvpState.PROCESSING,
                config=config,
            )
            return self._generation

    def process(self, generation: int, path: str | Path) -> ImageMvpSnapshot:
        """Run one pipeline generation and publish only a complete terminal result."""
        with self._lock:
            if generation != self._generation:
                return self._snapshot
            cancel_event = self._cancel_event
            config = self._snapshot.config

        try:
            local_path = validate_local_path(Path(path), field_name="input")
            preprocessing = self._preprocess(local_path, config.preprocessing)
            if cancel_event.is_set():
                return self._cancelled_or_current(generation)
            result = self._build_timeline(
                preprocessing,
                config.algorithm,
                sample_count=config.sample_count,
                harmonic_count=config.harmonic_count,
                speed=config.speed,
                boundary_parameters=config.boundary_parameters,
                canny_parameters=config.canny_parameters,
            )
            if cancel_event.is_set():
                return self._cancelled_or_current(generation)
        except ImageInputError:
            return self._publish_error(generation, cancel_event, "image_mvp.error.image_input")
        except EdgeDetectionError:
            return self._publish_error(generation, cancel_event, "image_mvp.error.edge")
        except ContourExtractionError:
            return self._publish_error(generation, cancel_event, "image_mvp.error.contour")
        except LocalPathError:
            return self._publish_error(generation, cancel_event, "image_mvp.error.local_path")
        except DomainValidationError:
            return self._publish_error(generation, cancel_event, "image_mvp.error.validation")
        except Exception:
            # This is the application/UI trust boundary: internal details and paths are not shown.
            return self._publish_error(generation, cancel_event, "image_mvp.error.runtime")

        with self._lock:
            if (
                generation != self._generation
                or cancel_event is not self._cancel_event
                or cancel_event.is_set()
            ):
                return self._snapshot
            if isinstance(result, ImageContourTimelineResult):
                self._snapshot = ImageMvpSnapshot(
                    generation=generation,
                    state=ImageMvpState.READY,
                    config=config,
                    result=result,
                    frame=result.timeline.snapshot(),
                )
            else:
                self._snapshot = ImageMvpSnapshot(
                    generation=generation,
                    state=ImageMvpState.EMPTY,
                    config=config,
                    result=result,
                )
            return self._snapshot

    def cancel(self) -> ImageMvpSnapshot:
        with self._lock:
            if self._snapshot.state is not ImageMvpState.PROCESSING:
                return self._snapshot
            self._cancel_event.set()
            self._snapshot = ImageMvpSnapshot(
                generation=self._generation,
                state=ImageMvpState.CANCELLED,
                config=self._snapshot.config,
            )
            return self._snapshot

    def play(self) -> ImageMvpSnapshot:
        return self._update_timeline("play")

    def pause(self) -> ImageMvpSnapshot:
        return self._update_timeline("pause")

    def restart(self) -> ImageMvpSnapshot:
        return self._update_timeline("restart")

    def tick(self, delta_seconds: float) -> ImageMvpSnapshot:
        return self._update_timeline("advance", delta_seconds)

    def set_speed(self, speed: float) -> ImageMvpSnapshot:
        normalized = validate_timeline_speed(speed)
        with self._lock:
            result = self._ready_result()
            if result is None:
                return self._snapshot
            frame = result.timeline.set_speed(normalized)
            config = replace(self._snapshot.config, speed=normalized)
            self._snapshot = replace(self._snapshot, config=config, frame=frame)
            return self._snapshot

    def set_harmonic_count(self, harmonic_count: int) -> ImageMvpSnapshot:
        with self._lock:
            result = self._ready_result()
            if result is None:
                return self._snapshot
            frame = result.timeline.set_harmonic_count(harmonic_count)
            config = replace(self._snapshot.config, harmonic_count=harmonic_count)
            self._snapshot = replace(self._snapshot, config=config, frame=frame)
            return self._snapshot

    def _update_timeline(self, action: str, *args: float) -> ImageMvpSnapshot:
        with self._lock:
            result = self._ready_result()
            if result is None:
                return self._snapshot
            operation = getattr(result.timeline, action)
            frame = operation(*args)
            self._snapshot = replace(self._snapshot, frame=frame)
            return self._snapshot

    def _ready_result(self) -> ImageContourTimelineResult | None:
        if self._snapshot.state is not ImageMvpState.READY or not isinstance(
            self._snapshot.result, ImageContourTimelineResult
        ):
            return None
        return self._snapshot.result

    def _cancelled_or_current(self, generation: int) -> ImageMvpSnapshot:
        with self._lock:
            if generation == self._generation and self._snapshot.state is ImageMvpState.PROCESSING:
                self._snapshot = ImageMvpSnapshot(
                    generation=generation,
                    state=ImageMvpState.CANCELLED,
                    config=self._snapshot.config,
                )
            return self._snapshot

    def _publish_error(
        self,
        generation: int,
        cancel_event: Event,
        failure_key: str,
    ) -> ImageMvpSnapshot:
        with self._lock:
            if (
                generation != self._generation
                or cancel_event is not self._cancel_event
                or cancel_event.is_set()
            ):
                return self._snapshot
            self._snapshot = ImageMvpSnapshot(
                generation=generation,
                state=ImageMvpState.ERROR,
                config=self._snapshot.config,
                failure_key=failure_key,
            )
            return self._snapshot
