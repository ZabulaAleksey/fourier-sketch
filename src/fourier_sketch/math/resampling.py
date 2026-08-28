"""Deterministic curve cleanup and the explicit index-sampling baseline."""

from bisect import bisect_right
from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from math import floor, fsum, hypot, isfinite, sqrt

from fourier_sketch.domain import Curve, DomainValidationError, Point2D

MAX_RESAMPLED_POINTS = 4096


class ResamplingMethod(StrEnum):
    """Explicit selectable parameterization methods."""

    UNIFORM_INDEX = "uniform_index"
    ARC_LENGTH = "arc_length"


@dataclass(frozen=True, slots=True)
class CurveSpacingMetrics:
    """Measured adjacent-segment spacing for one explicit curve topology."""

    segment_count: int
    total_length: float
    mean_length: float
    minimum_length: float
    maximum_length: float
    standard_deviation: float
    coefficient_of_variation: float

    def __post_init__(self) -> None:
        if (
            isinstance(self.segment_count, bool)
            or not isinstance(self.segment_count, int)
            or self.segment_count < 1
        ):
            raise DomainValidationError("spacing segment_count must be a positive integer")
        values = (
            self.total_length,
            self.mean_length,
            self.minimum_length,
            self.maximum_length,
            self.standard_deviation,
            self.coefficient_of_variation,
        )
        if any(
            not isinstance(value, float) or not isfinite(value) or value < 0.0 for value in values
        ):
            raise DomainValidationError("spacing metrics must be finite non-negative floats")
        if self.total_length <= 0.0 or self.mean_length <= 0.0:
            raise DomainValidationError("spacing metrics require positive total and mean length")
        if self.minimum_length > self.maximum_length:
            raise DomainValidationError("spacing minimum must not exceed maximum")


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


def resample_curve_by_arc_length(curve: Curve, sample_count: int) -> Curve:
    """Linearly resample a polyline at uniform cumulative arc-length positions."""
    if not isinstance(curve, Curve):
        raise DomainValidationError("curve must be a Curve")
    count = _validated_sample_count(sample_count)
    points = cleanup_consecutive_duplicates(curve.points)
    segment_ends = points[1:] + ((points[0],) if curve.closed else ())
    segment_starts = points if curve.closed else points[:-1]
    lengths = tuple(
        _finite_distance(start, end)
        for start, end in zip(segment_starts, segment_ends, strict=True)
    )
    total_length = _finite_sum(lengths, field_name="arc-length total")
    if not isfinite(total_length) or total_length <= 0.0:
        raise DomainValidationError("arc-length resampling requires positive finite total length")
    if count == 1:
        return Curve((points[0],), closed=curve.closed)

    cumulative = [0.0]
    for length in lengths:
        next_length = cumulative[-1] + length
        if not isfinite(next_length):
            raise DomainValidationError("arc-length cumulative length must be finite")
        cumulative.append(next_length)
    cumulative[-1] = total_length
    cumulative_values = tuple(cumulative)
    targets = (
        tuple(total_length * (output_index / count) for output_index in range(count))
        if curve.closed
        else tuple(total_length * (output_index / (count - 1)) for output_index in range(count))
    )
    output = tuple(
        points[0]
        if output_index == 0
        else points[-1]
        if not curve.closed and output_index == count - 1
        else _interpolate_at_length(
            segment_starts,
            segment_ends,
            lengths,
            cumulative_values,
            target,
        )
        for output_index, target in enumerate(targets)
    )
    return Curve(output, closed=curve.closed)


def curve_spacing_metrics(curve: Curve) -> CurveSpacingMetrics:
    """Measure consecutive spacing, including the seam only for closed curves."""
    if not isinstance(curve, Curve):
        raise DomainValidationError("curve must be a Curve")
    starts = curve.points if curve.closed else curve.points[:-1]
    ends = curve.points[1:] + ((curve.points[0],) if curve.closed else ())
    lengths = tuple(_finite_distance(start, end) for start, end in zip(starts, ends, strict=True))
    if not lengths:
        raise DomainValidationError("spacing metrics require at least one segment")
    total = _finite_sum(lengths, field_name="spacing total")
    if not isfinite(total) or total <= 0.0:
        raise DomainValidationError("spacing metrics require positive finite total length")
    mean = total / len(lengths)
    if not isfinite(mean) or mean <= 0.0:
        raise DomainValidationError("spacing mean must be positive and finite")
    try:
        squared_differences = tuple((length - mean) ** 2 for length in lengths)
    except OverflowError as error:
        raise DomainValidationError("spacing variance must be finite") from error
    variance = _finite_sum(squared_differences, field_name="spacing variance") / len(lengths)
    deviation = sqrt(variance)
    return CurveSpacingMetrics(
        segment_count=len(lengths),
        total_length=float(total),
        mean_length=float(mean),
        minimum_length=float(min(lengths)),
        maximum_length=float(max(lengths)),
        standard_deviation=float(deviation),
        coefficient_of_variation=float(deviation / mean),
    )


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


def _interpolate_at_length(
    starts: tuple[Point2D, ...],
    ends: tuple[Point2D, ...],
    lengths: tuple[float, ...],
    cumulative: tuple[float, ...],
    target: float,
) -> Point2D:
    segment_index = min(bisect_right(cumulative, target) - 1, len(lengths) - 1)
    while lengths[segment_index] == 0.0 and segment_index < len(lengths) - 1:
        segment_index += 1
    length = lengths[segment_index]
    if length == 0.0:
        raise DomainValidationError("arc-length interpolation reached a zero-length segment")
    fraction = (target - cumulative[segment_index]) / length
    fraction = min(max(fraction, 0.0), 1.0)
    return _weighted_interpolate(starts[segment_index], ends[segment_index], fraction)


def _interpolate(start: Point2D, end: Point2D, fraction: float) -> Point2D:
    return Point2D(
        start.x + (end.x - start.x) * fraction,
        start.y + (end.y - start.y) * fraction,
    )


def _weighted_interpolate(start: Point2D, end: Point2D, fraction: float) -> Point2D:
    complement = 1.0 - fraction
    return Point2D(
        complement * start.x + fraction * end.x,
        complement * start.y + fraction * end.y,
    )


def _finite_distance(start: Point2D, end: Point2D) -> float:
    distance = hypot(end.x - start.x, end.y - start.y)
    if not isfinite(distance):
        raise DomainValidationError("curve segment length must be finite")
    return distance


def _finite_sum(values: Iterable[float], *, field_name: str) -> float:
    try:
        result = fsum(values)
    except OverflowError as error:
        raise DomainValidationError(f"{field_name} must be finite") from error
    if not isfinite(result):
        raise DomainValidationError(f"{field_name} must be finite")
    return result
