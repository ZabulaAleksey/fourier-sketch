"""Transactional application boundary for the FS-014 skeleton diagnostic."""

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from threading import Event, Lock
from typing import Protocol

from fourier_sketch.domain import DomainValidationError
from fourier_sketch.imaging import (
    ImageInputError,
    ImagePreprocessingOptions,
    ImagePreprocessingResult,
    RasterImage,
    SkeletonAlgorithm,
    SkeletonizationError,
    SkeletonizationResult,
    export_raster_png,
    skeletonize_binary,
)

from .image_preprocessing import preprocess_local_image
from .local_paths import LocalPathError, validate_local_path


@dataclass(frozen=True, slots=True)
class LocalSkeletonResult:
    """Complete preprocessing and skeleton values published as one application result."""

    preprocessing: ImagePreprocessingResult
    skeletonization: SkeletonizationResult

    def __post_init__(self) -> None:
        if not isinstance(self.preprocessing, ImagePreprocessingResult) or not isinstance(
            self.skeletonization, SkeletonizationResult
        ):
            raise DomainValidationError("local skeleton result requires typed pipeline values")
        if self.preprocessing.binary != self.skeletonization.source:
            raise DomainValidationError("skeleton source must be the preprocessing binary raster")


class SkeletonState(StrEnum):
    """Observable lifecycle for one skeleton-processing generation."""

    INITIAL = "initial"
    PROCESSING = "processing"
    READY = "ready"
    EMPTY = "empty"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class SkeletonConfig:
    """Explicit preprocessing and thinning choices for one generation."""

    preprocessing: ImagePreprocessingOptions = field(default_factory=ImagePreprocessingOptions)
    algorithm: SkeletonAlgorithm = SkeletonAlgorithm.LEE

    def __post_init__(self) -> None:
        if not isinstance(self.preprocessing, ImagePreprocessingOptions):
            raise DomainValidationError("skeleton config requires preprocessing options")
        if self.algorithm is not SkeletonAlgorithm.LEE:
            raise DomainValidationError("FS-014 supports only the explicit Lee algorithm")


@dataclass(frozen=True, slots=True)
class SkeletonSnapshot:
    """Immutable generation publish point without observable partial results."""

    generation: int
    state: SkeletonState
    config: SkeletonConfig
    result: LocalSkeletonResult | None = None
    failure_key: str | None = None

    def __post_init__(self) -> None:
        if type(self.generation) is not int or self.generation < 0:
            raise DomainValidationError("skeleton generation must be a non-negative integer")
        if not isinstance(self.state, SkeletonState) or not isinstance(self.config, SkeletonConfig):
            raise DomainValidationError("skeleton snapshot requires typed state and config")
        if self.state in (SkeletonState.READY, SkeletonState.EMPTY):
            if not isinstance(self.result, LocalSkeletonResult) or self.failure_key is not None:
                raise DomainValidationError("terminal skeleton state requires only a result")
            if self.state is SkeletonState.READY and self.result.skeletonization.is_empty:
                raise DomainValidationError("ready skeleton state cannot contain an empty result")
            if self.state is SkeletonState.EMPTY and not self.result.skeletonization.is_empty:
                raise DomainValidationError("skeleton empty state is inconsistent with the result")
            return
        if self.state is SkeletonState.ERROR:
            if (
                self.result is not None
                or not isinstance(self.failure_key, str)
                or not self.failure_key
            ):
                raise DomainValidationError("failed skeleton state requires only a failure key")
            return
        if self.result is not None or self.failure_key is not None:
            raise DomainValidationError(
                "non-terminal skeleton state cannot expose a partial result"
            )


_PreprocessImage = Callable[
    [str | Path, ImagePreprocessingOptions],
    ImagePreprocessingResult,
]


class _Skeletonize(Protocol):
    def __call__(
        self,
        source: RasterImage,
        algorithm: SkeletonAlgorithm = SkeletonAlgorithm.LEE,
        *,
        cancellation_check: Callable[[], bool] | None = None,
    ) -> SkeletonizationResult: ...


def build_local_skeleton(
    path: str | Path,
    config: SkeletonConfig | None = None,
    *,
    cancellation_check: Callable[[], bool] | None = None,
) -> LocalSkeletonResult:
    """Run the real FS-010 binary pipeline and one explicit thinning backend."""
    if config is None:
        config = SkeletonConfig()
    if not isinstance(config, SkeletonConfig):
        raise DomainValidationError("local skeleton build requires a typed config")
    local_path = validate_local_path(Path(path), field_name="input")
    preprocessing = preprocess_local_image(local_path, config.preprocessing)
    skeletonization = skeletonize_binary(
        preprocessing.binary,
        config.algorithm,
        cancellation_check=cancellation_check,
    )
    return LocalSkeletonResult(preprocessing, skeletonization)


def export_local_skeleton(
    result: LocalSkeletonResult,
    destination: str | Path,
    *,
    overwrite: bool = False,
) -> None:
    """Export only the actual binary skeleton through the existing atomic PNG boundary."""
    if not isinstance(result, LocalSkeletonResult):
        raise DomainValidationError("skeleton export requires a typed result")
    target = validate_local_path(Path(destination), field_name="output")
    export_raster_png(result.skeletonization.skeleton, target, overwrite=overwrite)


class SkeletonController:
    """Publish complete skeleton results and suppress cancelled or stale generations."""

    def __init__(
        self,
        *,
        preprocess: _PreprocessImage = preprocess_local_image,
        skeletonize: _Skeletonize = skeletonize_binary,
    ) -> None:
        self._preprocess = preprocess
        self._skeletonize = skeletonize
        self._lock = Lock()
        self._generation = 0
        self._cancel_event = Event()
        self._snapshot = SkeletonSnapshot(0, SkeletonState.INITIAL, SkeletonConfig())

    def snapshot(self) -> SkeletonSnapshot:
        with self._lock:
            return self._snapshot

    def begin(self, config: SkeletonConfig) -> int:
        if not isinstance(config, SkeletonConfig):
            raise DomainValidationError("skeleton processing requires a typed config")
        with self._lock:
            self._cancel_event.set()
            self._generation += 1
            self._cancel_event = Event()
            self._snapshot = SkeletonSnapshot(
                self._generation,
                SkeletonState.PROCESSING,
                config,
            )
            return self._generation

    def process(self, generation: int, path: str | Path) -> SkeletonSnapshot:
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
            skeletonization = self._skeletonize(
                preprocessing.binary,
                config.algorithm,
                cancellation_check=cancel_event.is_set,
            )
            result = LocalSkeletonResult(preprocessing, skeletonization)
            if cancel_event.is_set():
                return self._cancelled_or_current(generation)
        except ImageInputError:
            return self._publish_error(generation, cancel_event, "skeleton.error.image_input")
        except SkeletonizationError as error:
            return self._publish_error(
                generation,
                cancel_event,
                f"skeleton.error.{error.code.value}",
            )
        except LocalPathError:
            return self._publish_error(generation, cancel_event, "skeleton.error.local_path")
        except DomainValidationError:
            return self._publish_error(generation, cancel_event, "skeleton.error.validation")
        except Exception:
            # Final application trust boundary: private backend/path detail is not user-facing.
            return self._publish_error(generation, cancel_event, "skeleton.error.runtime")
        with self._lock:
            if (
                generation != self._generation
                or cancel_event is not self._cancel_event
                or cancel_event.is_set()
            ):
                return self._snapshot
            state = SkeletonState.EMPTY if result.skeletonization.is_empty else SkeletonState.READY
            self._snapshot = SkeletonSnapshot(generation, state, config, result=result)
            return self._snapshot

    def cancel(self) -> SkeletonSnapshot:
        with self._lock:
            if self._snapshot.state is not SkeletonState.PROCESSING:
                return self._snapshot
            self._cancel_event.set()
            self._snapshot = SkeletonSnapshot(
                self._generation,
                SkeletonState.CANCELLED,
                self._snapshot.config,
            )
            return self._snapshot

    def _cancelled_or_current(self, generation: int) -> SkeletonSnapshot:
        with self._lock:
            if generation == self._generation and self._snapshot.state is SkeletonState.PROCESSING:
                self._snapshot = SkeletonSnapshot(
                    generation,
                    SkeletonState.CANCELLED,
                    self._snapshot.config,
                )
            return self._snapshot

    def _publish_error(
        self,
        generation: int,
        cancel_event: Event,
        failure_key: str,
    ) -> SkeletonSnapshot:
        with self._lock:
            if (
                generation != self._generation
                or cancel_event is not self._cancel_event
                or cancel_event.is_set()
            ):
                return self._snapshot
            self._snapshot = SkeletonSnapshot(
                generation,
                SkeletonState.ERROR,
                self._snapshot.config,
                failure_key=failure_key,
            )
            return self._snapshot
