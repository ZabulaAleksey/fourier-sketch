"""Integration contract from a real Curve spectrum to renderer-ready chain geometry."""

from cmath import exp
from math import pi

import pytest

from fourier_sketch.domain import Curve, Point2D, SpectrumOrdering
from fourier_sketch.math import (
    build_epicycle_chain,
    curve_to_complex_samples,
    fft_dft,
    reconstruct_at,
    select_first,
)

pytestmark = pytest.mark.integration

ABS_TOL = 1e-10


def test_circle_curve_flows_to_public_renderer_ready_chain() -> None:
    sample_count = 32
    samples = tuple(exp(2j * pi * index / sample_count) for index in range(sample_count))
    curve = Curve(
        tuple(Point2D(value.real, value.imag) for value in samples),
        closed=True,
    )
    spectrum = fft_dft(curve_to_complex_samples(curve))
    selection = select_first(spectrum, 3, SpectrumOrdering.AMPLITUDE_DESCENDING)

    chain = build_epicycle_chain(selection, 0.375)

    assert chain.vector_count == 3
    assert chain.vectors[0].frequency == 1
    assert all(
        vector.start == center
        for vector, center in zip(chain.vectors, chain.centers, strict=True)
    )
    assert complex(chain.endpoint.x, chain.endpoint.y) == pytest.approx(
        reconstruct_at(selection, 0.375),
        abs=ABS_TOL,
    )
