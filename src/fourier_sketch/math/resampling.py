"""Deterministic curve cleanup and the explicit index-sampling baseline."""

from collections.abc import Iterable
from math import floor

from fourier_sketch.domain import Curve, DomainValidationError, Point2D

MAX_RESAMPLED_POINTS = 4096


def cleanup_consecutive_duplicates(points: Iterable[Point2D]) -> tuple[Point2D, ...]:
    """Remove only adjacent duplicate points while preserving source order."""
    try:
        source = tuple(points)
    except TypeError as error:
        raise DomainValidationError("points must be an iterable of Point2D values") from error
    if any(not isinstance(point, Point2D) for point in source):
        raise DomainValidationError("points must contain only Point2D values")

    cleaned: list[Point2D] = []
    for point in source:
        if not cleaned or point != cleaned[-1]:
            cleaned.append(point)
    return tuple(cleaned)


def resample_curve_by_index(curve: Curve, sample_count: int) -> Curve:
    """Linearly resample over source indices without claiming arc-length uniformity."""
    if not isinstance(curve, Curve):
        raise DomainValidationError("curve must be a Curve")
    count = _validated_sample_count(sample_count)
    points = cleanup_consecutive_duplicates(curve.points)
    if not points:
        raise DomainValidationError("curve cleanup must retain at least one point")
    if len(points) == 1 or count == 1:
        return Curve((points[0],), closed=curve.closed)

    if curve.closed:
        output = tuple(
            points[0]
            if output_index == 0
            else _interpolate_closed(points, output_index * len(points) / count)
            for output_index in range(count)
        )
    else:
        output = tuple(
            points[0]
            if output_index == 0
            else points[-1]
            if output_index == count - 1
            else _interpolate_open(
                points,
                output_index * (len(points) - 1) / (count - 1),
            )
            for output_index in range(count)
        )
    return Curve(output, closed=curve.closed)


def _validated_sample_count(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise DomainValidationError("sample_count must be an integer")
    if value < 1 or value > MAX_RESAMPLED_POINTS:
        raise DomainValidationError(f"sample_count must be between 1 and {MAX_RESAMPLED_POINTS}")
    return value


def _interpolate_open(points: tuple[Point2D, ...], position: float) -> Point2D:
    left_index = min(floor(position), len(points) - 2)
    fraction = position - left_index
    return _interpolate(points[left_index], points[left_index + 1], fraction)


def _interpolate_closed(points: tuple[Point2D, ...], position: float) -> Point2D:
    left_index = floor(position) % len(points)
    fraction = position - floor(position)
    return _interpolate(points[left_index], points[(left_index + 1) % len(points)], fraction)


def _interpolate(start: Point2D, end: Point2D, fraction: float) -> Point2D:
    return Point2D(
        start.x + (end.x - start.x) * fraction,
        start.y + (end.y - start.y) * fraction,
    )
