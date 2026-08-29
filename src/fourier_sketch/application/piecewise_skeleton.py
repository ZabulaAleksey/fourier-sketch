"""Application composition for FS-016 graph-to-piecewise conversion."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from fourier_sketch.domain import DomainValidationError
from fourier_sketch.imaging import ImagePreprocessingOptions
from fourier_sketch.routing import PiecewiseComponentResult, build_piecewise_components

from .skeleton_graph import LocalSkeletonGraphResult, build_local_skeleton_graph


@dataclass(frozen=True, slots=True)
class LocalPiecewiseResult:
    """One complete local-image to explicit piecewise-curve transaction."""

    skeleton_graph: LocalSkeletonGraphResult
    conversion: PiecewiseComponentResult

    def __post_init__(self) -> None:
        if not isinstance(self.skeleton_graph, LocalSkeletonGraphResult) or not isinstance(
            self.conversion, PiecewiseComponentResult
        ):
            raise DomainValidationError("local piecewise result requires typed pipeline values")
        if self.conversion.graph != self.skeleton_graph.graph:
            raise DomainValidationError("piecewise conversion must retain its source graph")


def build_local_piecewise(
    path: str | Path,
    preprocessing: ImagePreprocessingOptions | None = None,
    *,
    cancellation_check: Callable[[], bool] | None = None,
) -> LocalPiecewiseResult:
    """Run decode, threshold, Lee skeleton, graph and all-or-nothing conversion."""
    graph = build_local_skeleton_graph(
        path,
        preprocessing,
        cancellation_check=cancellation_check,
    )
    conversion = build_piecewise_components(
        graph.graph,
        cancellation_check=cancellation_check,
    )
    return LocalPiecewiseResult(graph, conversion)
