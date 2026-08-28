"""Integration contract for Curve → spectrum → IDFT → Curve."""

import pytest

from fourier_sketch.domain import Curve, Point2D
from fourier_sketch.math import (
    complex_samples_to_curve,
    curve_to_complex_samples,
    fft_dft,
    idft,
    reference_dft,
)

pytestmark = pytest.mark.integration


def test_curve_round_trip_through_real_fft_pipeline() -> None:
    curve = Curve(
        (
            Point2D(1.0, 0.0),
            Point2D(0.0, 1.0),
            Point2D(-1.0, 0.0),
            Point2D(0.0, -1.0),
        ),
        closed=True,
    )

    samples = curve_to_complex_samples(curve)
    reconstructed = idft(fft_dft(samples))
    result = complex_samples_to_curve(reconstructed, closed=curve.closed)

    assert result.closed is True
    assert tuple(point.x for point in result.points) == pytest.approx(
        tuple(point.x for point in curve.points), abs=1e-12
    )
    assert tuple(point.y for point in result.points) == pytest.approx(
        tuple(point.y for point in curve.points), abs=1e-12
    )


def test_curve_reference_and_numpy_paths_reconstruct_the_same_samples() -> None:
    curve = Curve(
        (
            Point2D(2.0, -1.0),
            Point2D(-3.0, 4.0),
            Point2D(0.5, 0.25),
        )
    )
    samples = curve_to_complex_samples(curve)

    reference_result = idft(reference_dft(samples))
    numpy_result = idft(fft_dft(samples))

    assert reference_result == pytest.approx(samples, abs=1e-12, rel=1e-12)
    assert numpy_result == pytest.approx(reference_result, abs=1e-12, rel=1e-12)
