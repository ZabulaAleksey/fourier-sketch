"""Bounded sampling of independent piecewise strokes for a shared Fourier timeline."""

from dataclasses import dataclass
from enum import StrEnum
from math import fsum, hypot, isfinite

from fourier_sketch.domain import Curve, DomainValidationError, PiecewiseCurve, Point2D

from .resampling import resample_curve_by_arc_length

MAX_PIECEWISE_SAMPLES = 4096


class PiecewiseAllocation(StrEnum):
    """How a finite sample budget is distributed between strokes."""

    PROPORTIONAL = "proportional"
    EQUAL = "equal"


@dataclass(frozen=True, slots=True)
class PiecewiseBoundary:
    """A pen-up jump between consecutive sampled strokes."""

    left_segment: int
    right_segment: int
    left_sample_index: int
    right_sample_index: int
    left: Point2D
    right: Point2D
    distance: float
    cyclic: bool = False


@dataclass(frozen=True, slots=True)
class PiecewiseSampled:
    """Sampled independent strokes and their explicit jump metadata."""

    curve: PiecewiseCurve
    allocation: PiecewiseAllocation
    boundaries: tuple[PiecewiseBoundary, ...]

    @property
    def sample_count(self) -> int:
        return self.curve.sample_count


def sample_piecewise_curve(
    curve: PiecewiseCurve,
    sample_count: int,
    *,
    allocation: PiecewiseAllocation = PiecewiseAllocation.PROPORTIONAL,
) -> PiecewiseSampled:
    """Resample each stroke without inserting bridge samples."""
    if not isinstance(curve, PiecewiseCurve):
        raise DomainValidationError("curve must be a PiecewiseCurve")
    if type(sample_count) is not int or sample_count < 2 or sample_count > MAX_PIECEWISE_SAMPLES:
        raise DomainValidationError("sample_count must be between 2 and 4096")
    if sample_count < curve.segment_count:
        raise DomainValidationError("sample_count must provide at least one sample per segment")
    if not isinstance(allocation, PiecewiseAllocation):
        raise DomainValidationError("allocation must be a PiecewiseAllocation")
    lengths = tuple(_length(segment) for segment in curve.segments)
    counts = _allocate(sample_count, lengths, allocation)
    sampled = tuple(
        _resample_segment(segment, count, length)
        for segment, count, length in zip(curve.segments, counts, lengths, strict=True)
    )
    offsets: list[int] = []
    offset = 0
    for segment in sampled:
        offsets.append(offset)
        offset += segment.sample_count
    boundaries = tuple(
        PiecewiseBoundary(
            index,
            (index + 1) % len(sampled),
            offsets[index] + segment.sample_count - 1,
            offsets[(index + 1) % len(sampled)],
            segment.end,
            sampled[(index + 1) % len(sampled)].start,
            hypot(
                sampled[(index + 1) % len(sampled)].start.x - segment.end.x,
                sampled[(index + 1) % len(sampled)].start.y - segment.end.y,
            ),
            index == len(sampled) - 1,
        )
        for index, segment in enumerate(sampled)
    )
    return PiecewiseSampled(PiecewiseCurve(sampled), allocation, boundaries)


def _length(curve: Curve) -> float:
    points = curve.points
    starts = points if curve.closed else points[:-1]
    ends = points[1:] + ((points[0],) if curve.closed else ())
    pairs = zip(starts, ends, strict=True)
    lengths = tuple(hypot(b.x - a.x, b.y - a.y) for a, b in pairs)
    if any(not isfinite(length) for length in lengths):
        raise DomainValidationError("piecewise segment length must be finite")
    try:
        total = fsum(lengths)
    except OverflowError as error:
        raise DomainValidationError("piecewise segment length must be finite") from error
    if not isfinite(total):
        raise DomainValidationError("piecewise segment length must be finite")
    return total


def _resample_segment(curve: Curve, sample_count: int, length: float) -> Curve:
    if length == 0.0:
        return Curve(tuple(curve.start for _ in range(sample_count)), closed=curve.closed)
    if not curve.closed or sample_count == 1:
        return resample_curve_by_arc_length(curve, sample_count)
    materialized = Curve((*curve.points, curve.start))
    sampled = resample_curve_by_arc_length(materialized, sample_count)
    return Curve(sampled.points, closed=True)


def _allocate(total: int, lengths: tuple[float, ...], mode: PiecewiseAllocation) -> tuple[int, ...]:
    count = len(lengths)
    remaining = total - count
    if mode is PiecewiseAllocation.EQUAL:
        base, extra = divmod(remaining, count)
        return tuple(1 + base + (index < extra) for index in range(count))
    try:
        total_length = fsum(lengths)
    except OverflowError as error:
        raise DomainValidationError(
            "piecewise allocation length must be positive and finite"
        ) from error
    if not isfinite(total_length) or total_length < 0.0:
        raise DomainValidationError("piecewise allocation length must be finite and non-negative")
    if total_length == 0.0:
        base, extra = divmod(remaining, count)
        return tuple(1 + base + (index < extra) for index in range(count))
    raw = tuple(remaining * (length / total_length) for length in lengths)
    floors = tuple(int(value) for value in raw)
    left = remaining - sum(floors)
    order = sorted(range(count), key=lambda index: (-(raw[index] - floors[index]), index))
    result = list(floors)
    for index in order[:left]:
        result[index] += 1
    return tuple(1 + value for value in result)
