"""Unit contracts for the explicit uniform-by-index resampling baseline."""

from typing import cast

import pytest

from fourier_sketch.domain import Curve, DomainValidationError, Point2D
from fourier_sketch.math import cleanup_consecutive_duplicates, resample_curve_by_index

pytestmark = pytest.mark.unit


def test_cleanup_removes_only_consecutive_duplicates() -> None:
    first = Point2D(0.0, 0.0)
    second = Point2D(1.0, 0.0)

    assert cleanup_consecutive_duplicates((first, first, second, first)) == (
        first,
        second,
        first,
    )


def test_open_index_resampling_preserves_endpoints_and_interpolates_indices() -> None:
    curve = Curve(
        (Point2D(0.0, 0.0), Point2D(2.0, 0.0), Point2D(2.0, 2.0)),
        closed=False,
    )

    result = resample_curve_by_index(curve, 5)

    assert result.points == (
        Point2D(0.0, 0.0),
        Point2D(1.0, 0.0),
        Point2D(2.0, 0.0),
        Point2D(2.0, 1.0),
        Point2D(2.0, 2.0),
    )
    assert result.closed is False


def test_closed_index_resampling_includes_seam_without_duplicate_endpoint() -> None:
    curve = Curve(
        (
            Point2D(0.0, 0.0),
            Point2D(1.0, 0.0),
            Point2D(1.0, 1.0),
            Point2D(0.0, 1.0),
        ),
        closed=True,
    )

    result = resample_curve_by_index(curve, 8)

    assert result.sample_count == 8
    assert result.points[0] == curve.points[0]
    assert result.points[-1] == Point2D(0.0, 0.5)
    assert result.points[-1] != result.points[0]
    assert result.closed is True


def test_one_point_input_stays_one_point_dc_source() -> None:
    point = Point2D(2.0, -3.0)

    result = resample_curve_by_index(Curve((point,), closed=True), 128)

    assert result == Curve((point,), closed=True)


@pytest.mark.parametrize("count", [0, -1, 4097, 1.5, True])
def test_invalid_sample_count_is_rejected(count: object) -> None:
    curve = Curve((Point2D(0.0, 0.0),), closed=False)

    with pytest.raises(DomainValidationError, match="sample_count"):
        resample_curve_by_index(curve, cast(int, count))


def test_invalid_curve_and_point_collection_are_rejected() -> None:
    with pytest.raises(DomainValidationError, match="curve"):
        resample_curve_by_index(cast(Curve, None), 2)
    with pytest.raises(DomainValidationError, match="Point2D"):
        cleanup_consecutive_duplicates(cast(tuple[Point2D, ...], ("bad",)))
