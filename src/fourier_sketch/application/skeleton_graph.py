"""Application composition and atomic JSON export for the FS-015 skeleton graph."""

import os
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from fourier_sketch.domain import DomainValidationError
from fourier_sketch.imaging import ImagePreprocessingOptions
from fourier_sketch.imaging.skeleton_graph import build_skeleton_graph
from fourier_sketch.imaging.skeleton_graph_model import SkeletonGraphResult

from .local_paths import validate_local_path
from .skeletonization import LocalSkeletonResult, SkeletonConfig, build_local_skeleton


@dataclass(frozen=True, slots=True)
class LocalSkeletonGraphResult:
    """One complete local preprocessing, skeleton and graph transaction."""

    skeleton: LocalSkeletonResult
    graph: SkeletonGraphResult

    def __post_init__(self) -> None:
        if not isinstance(self.skeleton, LocalSkeletonResult) or not isinstance(
            self.graph, SkeletonGraphResult
        ):
            raise DomainValidationError("local skeleton graph requires typed pipeline results")
        if self.graph.source != self.skeleton.skeletonization:
            raise DomainValidationError("graph source must be the local skeleton result")


def build_local_skeleton_graph(
    path: str | Path,
    preprocessing: ImagePreprocessingOptions | None = None,
    *,
    cancellation_check: Callable[[], bool] | None = None,
) -> LocalSkeletonGraphResult:
    """Run the real local decode, Lee skeleton and topology transform."""
    if preprocessing is None:
        preprocessing = ImagePreprocessingOptions()
    if not isinstance(preprocessing, ImagePreprocessingOptions):
        raise DomainValidationError("skeleton graph preprocessing options must be typed")
    skeleton = build_local_skeleton(
        path,
        SkeletonConfig(preprocessing=preprocessing),
        cancellation_check=cancellation_check,
    )
    graph = build_skeleton_graph(
        skeleton.skeletonization,
        cancellation_check=cancellation_check,
    )
    return LocalSkeletonGraphResult(skeleton, graph)


def export_skeleton_graph_json(
    result: LocalSkeletonGraphResult,
    destination: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Publish canonical graph JSON atomically without implicit overwrite."""
    if not isinstance(result, LocalSkeletonGraphResult):
        raise DomainValidationError("graph export requires a typed local result")
    target = validate_local_path(Path(destination), field_name="output")
    if target.suffix.lower() != ".json":
        raise DomainValidationError("skeleton graph JSON output must use .json")
    if type(overwrite) is not bool or not target.parent.is_dir():
        raise DomainValidationError("skeleton graph export options are invalid")
    if target.exists() and not overwrite:
        raise FileExistsError(target.name)
    payload = result.graph.to_json_bytes()
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{target.stem}.",
            suffix=".tmp",
            dir=target.parent,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(payload)
            temporary.flush()
            os.fsync(temporary.fileno())
        if overwrite:
            os.replace(temporary_path, target)
            temporary_path = None
        else:
            os.link(temporary_path, target)
        return target
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
