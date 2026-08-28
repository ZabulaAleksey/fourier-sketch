"""Unit contracts for point/curve complex conversion."""

from typing import cast

import pytest

from fourier_sketch.domain import Curve, DomainValidationError, Point2D
from fourier_sketch.math import (
    complex_samples_to_curve,
    complex_to_point,
    curve_to_complex_samples,
    point_to_complex,
)

pytestmark = pytest.mark.unit


def test_point_conversion_is_bijective_for_finite_values() -> None:
    point = Point2D(-2.5, 4.25)

    assert point_to_complex(point) == -2.5 + 4.25j
    assert complex_to_point(point_to_complex(point)) == point


def test_curve_conversion_preserves_order_and_explicit_closed_flag() -> None:
    curve = Curve((Point2D(2.0, 0.0), Point2D(0.0, -3.0)), closed=True)
    samples = curve_to_complex_samples(curve)

    assert samples == (2.0 + 0.0j, 0.0 - 3.0j)
    assert complex_samples_to_curve(samples, closed=curve.closed) == curve


def test_conversion_rejects_malformed_or_non_finite_input() -> None:
    invalid_point = cast(Point2D, object())
    invalid_curve = cast(Curve, object())

    with pytest.raises(DomainValidationError, match="Point2D"):
        point_to_complex(invalid_point)
    with pytest.raises(DomainValidationError, match="Curve"):
        curve_to_complex_samples(invalid_curve)
    with pytest.raises(DomainValidationError, match="finite"):
        complex_to_point(complex(float("nan"), 0.0))
    with pytest.raises(DomainValidationError, match="at least one"):
        complex_samples_to_curve((), closed=False)
