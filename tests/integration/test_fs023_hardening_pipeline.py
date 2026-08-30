"""Representative numerical and resource regressions for FS-023."""

import tracemalloc
from math import cos, pi, sin

import pytest

from fourier_sketch.application import build_freehand_timeline
from fourier_sketch.domain import Curve, Point2D
from fourier_sketch.math import fft_dft, idft, reference_dft

pytestmark = pytest.mark.integration


def _signal(sample_count: int) -> tuple[complex, ...]:
    return tuple(
        complex(
            1.25 * cos(2.0 * pi * 7 * index / sample_count)
            + 1e-9 * cos(2.0 * pi * 131 * index / sample_count),
            0.75 * sin(2.0 * pi * 11 * index / sample_count),
        )
        for index in range(sample_count)
    )


def test_representative_large_fft_round_trip_is_finite_and_memory_bounded() -> None:
    samples = _signal(16_384)
    tracemalloc.start()
    reconstructed = idft(fft_dft(samples))
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    assert reconstructed == pytest.approx(samples, abs=2e-10, rel=2e-10)
    assert peak < 128 * 1024 * 1024


def test_optimized_inverse_matches_reference_at_oracle_scale() -> None:
    samples = _signal(512)

    assert idft(fft_dft(samples)) == pytest.approx(
        idft(reference_dft(samples)),
        abs=2e-10,
        rel=2e-10,
    )


def test_stress_harmonic_count_keeps_full_grid_parity() -> None:
    samples = _signal(4096)
    curve = Curve(
        tuple(Point2D(value.real, value.imag) for value in samples),
        closed=True,
    )

    frame = build_freehand_timeline(curve, harmonic_count=4096).snapshot()

    assert frame.selection.coefficient_count == 4096
    reconstructed = tuple(
        complex(point.x, point.y) for point in frame.reconstruction.points
    )
    assert reconstructed == pytest.approx(samples, abs=2e-10, rel=2e-10)
