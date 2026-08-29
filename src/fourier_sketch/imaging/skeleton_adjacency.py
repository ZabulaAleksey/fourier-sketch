"""Shared, deterministic raw skeleton adjacency policy."""

from __future__ import annotations

from collections.abc import Callable, Iterable

from fourier_sketch.domain import DomainValidationError

from .contour_model import PixelPoint
from .skeleton_graph_model import SKELETON_GRAPH_ADJACENCY_POLICY

CancellationCheck = Callable[[], bool]
_ORTHOGONAL = ((-1, 0), (0, -1), (0, 1), (1, 0))
_DIAGONAL = ((-1, -1), (-1, 1), (1, -1), (1, 1))


def raw_adjacency(
    points: Iterable[PixelPoint], *, cancellation_check: CancellationCheck | None = None
) -> dict[PixelPoint, tuple[PixelPoint, ...]]:
    """Return the canonical corner-suppressed 8-neighbour adjacency."""
    values = frozenset(points)
    if any(not isinstance(p, PixelPoint) for p in values):
        raise DomainValidationError("raw adjacency requires PixelPoint values")
    result: dict[PixelPoint, tuple[PixelPoint, ...]] = {}
    for i, point in enumerate(sorted(values, key=_key)):
        if i % 4096 == 0 and cancellation_check and cancellation_check():
            raise DomainValidationError("raw adjacency build cancelled")
        neighbors: list[PixelPoint] = []
        for dr, dc in _ORTHOGONAL + _DIAGONAL:
            column, row = point.column + dc, point.row + dr
            if column < 0 or row < 0:
                continue
            candidate = PixelPoint(column, row)
            if candidate not in values:
                continue
            if abs(dr) == 1 and abs(dc) == 1 and (
                (point.column + dc >= 0 and PixelPoint(point.column + dc, point.row) in values)
                or (point.row + dr >= 0 and PixelPoint(point.column, point.row + dr) in values)
            ):
                continue
            neighbors.append(candidate)
        result[point] = tuple(sorted(neighbors, key=_key))
    return result


def _key(p: PixelPoint) -> tuple[int, int]:
    return p.row, p.column


__all__ = ["SKELETON_GRAPH_ADJACENCY_POLICY", "raw_adjacency"]
