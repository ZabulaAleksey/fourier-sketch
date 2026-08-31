"""Deterministic curvature-weighted arc-length sampling."""

from bisect import bisect_right
from dataclasses import dataclass
from enum import StrEnum
from math import acos, fsum, hypot, isfinite, pi

from fourier_sketch.domain import Curve, DomainValidationError, Point2D

from .resampling import cleanup_consecutive_duplicates

ADAPTIVE_SAMPLING_ALGORITHM = "adaptive-weighted-arc-length-v1"
ADAPTIVE_SAMPLING_POLICY = "adaptive_weighted_arc_length_v1"
UNIFORM_ZERO_SIGNAL_POLICY = "uniform_arc_length_zero_adaptive_signal"
MAX_ADAPTIVE_SAMPLES = 4096
MAX_ADAPTIVE_SOURCE_POINTS = 250_000


class AdaptiveSamplingPolicy(StrEnum):
    """Stable provenance for weighted and pre-approved uniform behavior."""

    ADAPTIVE_WEIGHTED_ARC_LENGTH = ADAPTIVE_SAMPLING_POLICY
    UNIFORM_ARC_LENGTH_ZERO_ADAPTIVE_SIGNAL = UNIFORM_ZERO_SIGNAL_POLICY


@dataclass(frozen=True, slots=True)
class AdaptiveSamplingResult:
    source: Curve
    curve: Curve
    sample_count: int
    curvature_weight: float
    vertex_curvatures: tuple[float, ...]
    segment_lengths: tuple[float, ...]
    segment_densities: tuple[float, ...]
    total_density: float
    policy: AdaptiveSamplingPolicy
    algorithm: str = ADAPTIVE_SAMPLING_ALGORITHM

    def __post_init__(self) -> None:
        if not isinstance(self.source, Curve) or not isinstance(self.curve, Curve):
            raise DomainValidationError("adaptive result requires Curve values")
        if (
            type(self.sample_count) is not int
            or self.sample_count != self.curve.sample_count
            or self.source.closed != self.curve.closed
        ):
            raise DomainValidationError("adaptive result sample budget or topology is inconsistent")
        if (
            type(self.curvature_weight) is not float
            or not isfinite(self.curvature_weight)
            or not 0.0 <= self.curvature_weight <= 100.0
        ):
            raise DomainValidationError("adaptive result curvature weight is invalid")
        if not self.vertex_curvatures or any(
            type(value) is not float or not isfinite(value) or not 0.0 <= value <= 1.0
            for value in self.vertex_curvatures
        ):
            raise DomainValidationError("adaptive result curvatures are invalid")
        if (
            len(self.segment_lengths) != len(self.segment_densities)
            or not self.segment_lengths
            or any(
                type(value) is not float or not isfinite(value) or value <= 0.0
                for value in (*self.segment_lengths, *self.segment_densities)
            )
        ):
            raise DomainValidationError("adaptive result segment diagnostics are invalid")
        if (
            type(self.total_density) is not float
            or not isfinite(self.total_density)
            or self.total_density <= 0.0
        ):
            raise DomainValidationError("adaptive result total density is invalid")
        if not isinstance(self.policy, AdaptiveSamplingPolicy):
            raise DomainValidationError("adaptive result policy is invalid")
        if self.algorithm != ADAPTIVE_SAMPLING_ALGORITHM:
            raise DomainValidationError("adaptive result algorithm is invalid")


def resample_curve_adaptive(
    curve: Curve, sample_count: int, *, curvature_weight: float
) -> AdaptiveSamplingResult:
    if not isinstance(curve, Curve):
        raise DomainValidationError("adaptive sampling requires a Curve")
    if curve.sample_count > MAX_ADAPTIVE_SOURCE_POINTS:
        raise DomainValidationError(
            f"adaptive source must not exceed {MAX_ADAPTIVE_SOURCE_POINTS} points"
        )
    if (
        isinstance(sample_count, bool)
        or not isinstance(sample_count, int)
        or not 1 <= sample_count <= MAX_ADAPTIVE_SAMPLES
    ):
        raise DomainValidationError(
            f"adaptive sample_count must be between 1 and {MAX_ADAPTIVE_SAMPLES}"
        )
    if isinstance(curvature_weight, bool) or not isinstance(curvature_weight, (int, float)):
        raise DomainValidationError("curvature_weight must be a finite number between 0 and 100")
    weight = float(curvature_weight)
    if not isfinite(weight) or not 0.0 <= weight <= 100.0:
        raise DomainValidationError("curvature_weight must be a finite number between 0 and 100")
    points = cleanup_consecutive_duplicates(curve.points)
    if curve.closed and len(points) > 1 and points[-1] == points[0]:
        points = points[:-1]
    if len(points) < 2:
        raise DomainValidationError("adaptive sampling requires positive finite total length")
    starts = points[:-1] if not curve.closed else points
    ends = points[1:] if not curve.closed else (*points[1:], points[0])
    lengths = tuple(_distance(a, b) for a, b in zip(starts, ends, strict=True))
    if any(length <= 0.0 for length in lengths):
        raise DomainValidationError("adaptive sampling requires positive segment lengths")
    curvatures = _curvatures(points, curve.closed)
    densities = tuple(
        length * (1.0 + weight * (curvatures[i] + curvatures[(i + 1) % len(points)]) / 2.0)
        for i, length in enumerate(lengths)
    )
    try:
        total = fsum(densities)
    except OverflowError as error:
        raise DomainValidationError("adaptive total density must be finite") from error
    if not isfinite(total) or total <= 0.0:
        raise DomainValidationError("adaptive sampling requires positive finite total length")
    output = _sample(points, starts, ends, lengths, densities, total, sample_count, curve.closed)
    policy = (
        AdaptiveSamplingPolicy.UNIFORM_ARC_LENGTH_ZERO_ADAPTIVE_SIGNAL
        if weight == 0.0 or not any(curvatures)
        else AdaptiveSamplingPolicy.ADAPTIVE_WEIGHTED_ARC_LENGTH
    )
    return AdaptiveSamplingResult(
        curve,
        Curve(output, closed=curve.closed),
        sample_count,
        weight,
        curvatures,
        lengths,
        densities,
        float(total),
        policy,
    )


def _curvatures(points: tuple[Point2D, ...], closed: bool) -> tuple[float, ...]:
    result = []
    for i, point in enumerate(points):
        if not closed and i in (0, len(points) - 1):
            result.append(0.0)
            continue
        prev = points[(i - 1) % len(points)]
        nxt = points[(i + 1) % len(points)]
        a = (point.x - prev.x, point.y - prev.y)
        b = (nxt.x - point.x, nxt.y - point.y)
        la, lb = hypot(*a), hypot(*b)
        if la == 0.0 or lb == 0.0:
            result.append(0.0)
        else:
            unit_dot = (a[0] / la) * (b[0] / lb) + (a[1] / la) * (b[1] / lb)
            result.append(acos(min(1.0, max(-1.0, unit_dot))) / pi)
    return tuple(result)


def _sample(
    points: tuple[Point2D, ...],
    starts: tuple[Point2D, ...],
    ends: tuple[Point2D, ...],
    lengths: tuple[float, ...],
    densities: tuple[float, ...],
    total: float,
    count: int,
    closed: bool,
) -> tuple[Point2D, ...]:
    cumulative = [0.0]
    for value in densities:
        cumulative.append(cumulative[-1] + value)
    targets = (
        (total * i / count for i in range(count))
        if closed
        else (total * i / (count - 1) for i in range(count))
        if count > 1
        else (0.0,)
    )
    output = []
    for i, target in enumerate(targets):
        if i == 0:
            output.append(points[0])
            continue
        if not closed and i == count - 1:
            output.append(points[-1])
            continue
        index = min(bisect_right(cumulative, target) - 1, len(lengths) - 1)
        fraction = (target - cumulative[index]) / densities[index]
        output.append(
            Point2D(
                starts[index].x + (ends[index].x - starts[index].x) * fraction,
                starts[index].y + (ends[index].y - starts[index].y) * fraction,
            )
        )
    return tuple(output)


def _distance(a: Point2D, b: Point2D) -> float:
    value = hypot(b.x - a.x, b.y - a.y)
    if not isfinite(value):
        raise DomainValidationError("adaptive sampling geometry must be finite")
    return value
