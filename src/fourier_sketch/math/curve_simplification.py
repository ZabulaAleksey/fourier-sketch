"""Bounded deterministic Douglas-Peucker simplification for ordered curves."""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from enum import StrEnum
from itertools import pairwise
from math import fsum, hypot, isfinite, sqrt

from fourier_sketch.domain import Curve, DomainValidationError, Point2D

MAX_SIMPLIFICATION_POINTS = 250_000
DEFAULT_SIMPLIFICATION_EVALUATIONS = 10_000_000
MAX_SIMPLIFICATION_EVALUATIONS = 100_000_000
DOUGLAS_PEUCKER_ALGORITHM = "douglas-peucker-segment-v1"
CLOSED_ANCHOR_POLICY = "source-zero-farthest-lowest-index-v1"


class SimplificationFailureCode(StrEnum):
    """Stable controlled failures specific to bounded simplification work."""

    RESOURCE_LIMIT = "resource_limit"
    CANCELLED = "cancelled"


class CurveSimplificationError(DomainValidationError):
    """Typed failure that never carries a partial simplified curve."""

    def __init__(self, code: SimplificationFailureCode, message: str) -> None:
        if not isinstance(code, SimplificationFailureCode):
            raise DomainValidationError("simplification failure code is invalid")
        self.code = code
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class CurveSimplificationMetrics:
    """Measured reduction and retained-segment residuals, not a Hausdorff metric."""

    source_point_count: int
    simplified_point_count: int
    removed_point_count: int
    reduction_ratio: float
    source_length: float
    simplified_length: float
    absolute_length_delta: float
    maximum_segment_deviation: float
    rms_segment_deviation: float

    def __post_init__(self) -> None:
        counts = (
            self.source_point_count,
            self.simplified_point_count,
            self.removed_point_count,
        )
        if any(type(value) is not int or value < 0 for value in counts):
            raise DomainValidationError(
                "simplification metric counts must be non-negative integers"
            )
        if (
            self.source_point_count < 1
            or not 1 <= self.simplified_point_count <= self.source_point_count
        ):
            raise DomainValidationError("simplification metric point counts are inconsistent")
        if self.removed_point_count != self.source_point_count - self.simplified_point_count:
            raise DomainValidationError("simplification removed count is inconsistent")
        values = (
            self.reduction_ratio,
            self.source_length,
            self.simplified_length,
            self.absolute_length_delta,
            self.maximum_segment_deviation,
            self.rms_segment_deviation,
        )
        if any(type(value) is not float or not isfinite(value) or value < 0.0 for value in values):
            raise DomainValidationError("simplification metrics must be finite non-negative floats")
        if self.reduction_ratio > 1.0:
            raise DomainValidationError("simplification reduction ratio must not exceed one")


@dataclass(frozen=True, slots=True)
class DouglasPeuckerResult:
    """Immutable simplified source subsequence with explicit provenance and metrics."""

    source: Curve
    curve: Curve
    retained_indices: tuple[int, ...]
    tolerance: float
    distance_evaluations: int
    metrics: CurveSimplificationMetrics
    algorithm: str = DOUGLAS_PEUCKER_ALGORITHM
    closed_anchor_policy: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.source, Curve) or not isinstance(self.curve, Curve):
            raise DomainValidationError("simplification result requires Curve values")
        if self.source.closed != self.curve.closed:
            raise DomainValidationError("simplification must preserve curve topology")
        if (
            not isinstance(self.retained_indices, tuple)
            or not self.retained_indices
            or any(type(index) is not int for index in self.retained_indices)
            or tuple(sorted(set(self.retained_indices))) != self.retained_indices
        ):
            raise DomainValidationError(
                "simplification retained indices must be unique and ordered"
            )
        if self.retained_indices[0] < 0 or self.retained_indices[-1] >= self.source.sample_count:
            raise DomainValidationError("simplification retained index is outside the source")
        if self.curve.points != tuple(self.source.points[index] for index in self.retained_indices):
            raise DomainValidationError(
                "simplification curve must be the retained source subsequence"
            )
        if (
            type(self.tolerance) is not float
            or not isfinite(self.tolerance)
            or self.tolerance < 0.0
        ):
            raise DomainValidationError("simplification result tolerance is invalid")
        if type(self.distance_evaluations) is not int or self.distance_evaluations < 0:
            raise DomainValidationError("simplification evaluation count is invalid")
        if not isinstance(self.metrics, CurveSimplificationMetrics):
            raise DomainValidationError("simplification result requires typed metrics")
        if (
            self.metrics.source_point_count != self.source.sample_count
            or self.metrics.simplified_point_count != self.curve.sample_count
            or self.metrics.maximum_segment_deviation > self.tolerance
        ):
            raise DomainValidationError("simplification result metrics are inconsistent")
        if not self.source.closed and (
            self.retained_indices[0] != 0
            or self.retained_indices[-1] != self.source.sample_count - 1
        ):
            raise DomainValidationError("open simplification must preserve exact endpoints")
        if self.source.closed and self.retained_indices[0] != 0:
            raise DomainValidationError("closed simplification must preserve source index zero")
        if self.algorithm != DOUGLAS_PEUCKER_ALGORITHM:
            raise DomainValidationError("simplification algorithm provenance is invalid")
        expected_policy = CLOSED_ANCHOR_POLICY if self.source.closed else None
        if self.closed_anchor_policy != expected_policy:
            raise DomainValidationError("simplification closed-anchor provenance is invalid")


@dataclass(slots=True)
class _WorkBudget:
    maximum: int
    cancellation_check: Callable[[], bool] | None
    evaluations: int = 0

    def check_cancelled(self) -> None:
        callback = self.cancellation_check
        if callback is not None and callback():
            raise CurveSimplificationError(
                SimplificationFailureCode.CANCELLED,
                "curve simplification was cancelled",
            )

    def consume(self) -> None:
        self.evaluations += 1
        if self.evaluations > self.maximum:
            raise CurveSimplificationError(
                SimplificationFailureCode.RESOURCE_LIMIT,
                "curve simplification exceeded the distance-evaluation budget",
            )
        if self.evaluations % 1024 == 0:
            self.check_cancelled()


def simplify_curve_douglas_peucker(
    curve: Curve,
    tolerance: float,
    *,
    max_distance_evaluations: int = DEFAULT_SIMPLIFICATION_EVALUATIONS,
    cancellation_check: Callable[[], bool] | None = None,
) -> DouglasPeuckerResult:
    """Simplify an ordered curve transactionally within an explicit work budget."""

    if not isinstance(curve, Curve):
        raise DomainValidationError("curve simplification requires a Curve")
    if curve.sample_count > MAX_SIMPLIFICATION_POINTS:
        raise CurveSimplificationError(
            SimplificationFailureCode.RESOURCE_LIMIT,
            f"curve simplification source must not exceed {MAX_SIMPLIFICATION_POINTS} points",
        )
    normalized_tolerance = _validate_tolerance(tolerance)
    maximum = _validate_evaluation_budget(max_distance_evaluations)
    if cancellation_check is not None and not callable(cancellation_check):
        raise DomainValidationError("simplification cancellation_check must be callable")
    work = _WorkBudget(maximum, cancellation_check)
    work.check_cancelled()

    canonical_indices = _canonical_source_indices(curve)
    if curve.closed:
        retained = _simplify_closed(curve.points, canonical_indices, normalized_tolerance, work)
    else:
        retained = _simplify_open(curve.points, canonical_indices, normalized_tolerance, work)
    work.check_cancelled()
    simplified = Curve(tuple(curve.points[index] for index in retained), closed=curve.closed)
    metrics = _build_metrics(curve, simplified, retained, canonical_indices, work)
    work.check_cancelled()
    return DouglasPeuckerResult(
        source=curve,
        curve=simplified,
        retained_indices=retained,
        tolerance=normalized_tolerance,
        distance_evaluations=work.evaluations,
        metrics=metrics,
        closed_anchor_policy=CLOSED_ANCHOR_POLICY if curve.closed else None,
    )


def _canonical_source_indices(curve: Curve) -> tuple[int, ...]:
    indices = tuple(range(curve.sample_count))
    if curve.closed and len(indices) > 1 and curve.points[-1] == curve.points[0]:
        return indices[:-1]
    return indices


def _simplify_open(
    points: tuple[Point2D, ...],
    indices: tuple[int, ...],
    tolerance: float,
    work: _WorkBudget,
) -> tuple[int, ...]:
    if len(indices) <= 2:
        return indices
    retained = {0, len(indices) - 1}
    stack = [(0, len(indices) - 1)]
    while stack:
        left, right = stack.pop()
        if right - left <= 1:
            continue
        start = points[indices[left]]
        end = points[indices[right]]
        maximum_distance = -1.0
        split = -1
        for position in range(left + 1, right):
            work.consume()
            distance = _point_segment_distance(points[indices[position]], start, end)
            if distance > maximum_distance:
                maximum_distance = distance
                split = position
        if maximum_distance > tolerance:
            retained.add(split)
            stack.append((split, right))
            stack.append((left, split))
    return tuple(indices[position] for position in sorted(retained))


def _simplify_closed(
    points: tuple[Point2D, ...],
    indices: tuple[int, ...],
    tolerance: float,
    work: _WorkBudget,
) -> tuple[int, ...]:
    if len(indices) <= 3:
        return indices
    start = points[indices[0]]
    anchor_position = 1
    farthest_distance = -1.0
    for position in range(1, len(indices)):
        work.consume()
        distance = _point_distance(points[indices[position]], start)
        if distance > farthest_distance:
            farthest_distance = distance
            anchor_position = position
    first_arc = indices[: anchor_position + 1]
    second_arc = (*indices[anchor_position:], indices[0])
    retained = set(_simplify_open(points, first_arc, tolerance, work))
    retained.update(_simplify_open(points, second_arc, tolerance, work))
    if len(retained) < 3:
        third_position = _third_closed_anchor_position(
            points,
            indices,
            anchor_position,
            work,
        )
        retained = set()
        anchor_positions = tuple(sorted((0, anchor_position, third_position)))
        for left, right in pairwise(anchor_positions):
            retained.update(
                _simplify_open(points, indices[left : right + 1], tolerance, work)
            )
        seam_arc = (*indices[anchor_positions[-1] :], indices[0])
        retained.update(_simplify_open(points, seam_arc, tolerance, work))
    return tuple(index for index in indices if index in retained)


def _third_closed_anchor_position(
    points: tuple[Point2D, ...],
    indices: tuple[int, ...],
    second_anchor_position: int,
    work: _WorkBudget,
) -> int:
    start = points[indices[0]]
    second = points[indices[second_anchor_position]]
    third_position = next(
        position for position in range(1, len(indices)) if position != second_anchor_position
    )
    farthest_distance = -1.0
    for position in range(1, len(indices)):
        if position == second_anchor_position:
            continue
        work.consume()
        distance = _point_segment_distance(points[indices[position]], start, second)
        if distance > farthest_distance:
            farthest_distance = distance
            third_position = position
    return third_position


def _build_metrics(
    source: Curve,
    simplified: Curve,
    retained: tuple[int, ...],
    canonical_indices: tuple[int, ...],
    work: _WorkBudget,
) -> CurveSimplificationMetrics:
    deviations = _retained_segment_deviations(
        source.points,
        retained,
        canonical_indices,
        source.closed,
        work,
    )
    if source.closed and source.sample_count > len(canonical_indices):
        deviations = (*deviations, 0.0)
    squared = tuple(value * value for value in deviations)
    if any(not isfinite(value) for value in squared):
        raise DomainValidationError("simplification deviation metrics must remain finite")
    source_length = _curve_length(source.points, source.closed)
    simplified_length = _curve_length(simplified.points, simplified.closed)
    source_count = source.sample_count
    result_count = simplified.sample_count
    return CurveSimplificationMetrics(
        source_point_count=source_count,
        simplified_point_count=result_count,
        removed_point_count=source_count - result_count,
        reduction_ratio=float((source_count - result_count) / source_count),
        source_length=float(source_length),
        simplified_length=float(simplified_length),
        absolute_length_delta=float(abs(source_length - simplified_length)),
        maximum_segment_deviation=float(max(deviations, default=0.0)),
        rms_segment_deviation=float(sqrt(fsum(squared) / len(deviations))),
    )


def _retained_segment_deviations(
    points: tuple[Point2D, ...],
    retained: tuple[int, ...],
    canonical_indices: tuple[int, ...],
    closed: bool,
    work: _WorkBudget,
) -> tuple[float, ...]:
    index_position = {index: position for position, index in enumerate(canonical_indices)}
    deviations = [0.0] * len(canonical_indices)
    pairs = list(pairwise(retained))
    if closed and len(retained) > 1:
        pairs.append((retained[-1], retained[0]))
    for left_index, right_index in pairs:
        left = index_position[left_index]
        right = index_position[right_index]
        positions: Iterable[int]
        if right > left:
            positions = range(left + 1, right)
        else:
            positions = (*range(left + 1, len(canonical_indices)), *range(0, right))
        for position in positions:
            work.consume()
            deviations[position] = _point_segment_distance(
                points[canonical_indices[position]],
                points[left_index],
                points[right_index],
            )
    return tuple(deviations)


def _curve_length(points: tuple[Point2D, ...], closed: bool) -> float:
    if len(points) < 2:
        return 0.0
    ends = points[1:] + ((points[0],) if closed else ())
    starts = points if closed else points[:-1]
    lengths = tuple(_point_distance(start, end) for start, end in zip(starts, ends, strict=True))
    try:
        total = fsum(lengths)
    except OverflowError as error:
        raise DomainValidationError("simplification polyline length must remain finite") from error
    if not isfinite(total):
        raise DomainValidationError("simplification polyline length must remain finite")
    return total


def _point_distance(first: Point2D, second: Point2D) -> float:
    dx = second.x - first.x
    dy = second.y - first.y
    distance = hypot(dx, dy)
    if not isfinite(distance):
        raise DomainValidationError("simplification geometry must have finite distances")
    return distance


def _point_segment_distance(point: Point2D, start: Point2D, end: Point2D) -> float:
    dx = end.x - start.x
    dy = end.y - start.y
    length = hypot(dx, dy)
    if not isfinite(length):
        raise DomainValidationError("simplification segment length must remain finite")
    if length == 0.0:
        return _point_distance(point, start)
    offset_x = point.x - start.x
    offset_y = point.y - start.y
    if not isfinite(offset_x) or not isfinite(offset_y):
        raise DomainValidationError("simplification point offset must remain finite")
    unit_x = dx / length
    unit_y = dy / length
    projection = offset_x * unit_x + offset_y * unit_y
    if not isfinite(projection):
        raise DomainValidationError("simplification projection must remain finite")
    projection = min(max(projection, 0.0), length)
    nearest_x = start.x + unit_x * projection
    nearest_y = start.y + unit_y * projection
    distance = hypot(point.x - nearest_x, point.y - nearest_y)
    if not isfinite(distance):
        raise DomainValidationError("simplification distance must remain finite")
    return distance


def _validate_tolerance(value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DomainValidationError("simplification tolerance must be a finite non-negative number")
    normalized = float(value)
    if not isfinite(normalized) or normalized < 0.0:
        raise DomainValidationError("simplification tolerance must be a finite non-negative number")
    return normalized


def _validate_evaluation_budget(value: int) -> int:
    if type(value) is not int or not 1 <= value <= MAX_SIMPLIFICATION_EVALUATIONS:
        raise DomainValidationError(
            "simplification distance-evaluation budget must be between "
            f"1 and {MAX_SIMPLIFICATION_EVALUATIONS}"
        )
    return value
