"""Generated epicycle connectivity, permutation and reconstruction contracts."""

from itertools import pairwise

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from fourier_sketch.application import EpicycleTimeline, FrequencySoloSession
from fourier_sketch.domain import Curve, Point2D, SpectrumOrdering
from fourier_sketch.math import (
    build_epicycle_chain,
    fft_dft,
    reconstruct_at,
    reconstruct_samples,
    select_first,
    select_frequencies,
)

pytestmark = pytest.mark.property

ABS_TOL = 1e-10  # N<=8 and coordinate scale<=20; sequential sum accumulates O(N*eps).

finite_component = st.integers(min_value=-20, max_value=20).map(float)
complex_samples = st.lists(
    st.builds(complex, finite_component, finite_component),
    min_size=1,
    max_size=8,
).map(tuple)


@given(
    complex_samples,
    st.floats(min_value=-10.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    finite_component,
    finite_component,
)
def test_chain_connectivity_and_endpoint_match_reconstruction(
    samples: tuple[complex, ...],
    time: float,
    origin_x: float,
    origin_y: float,
) -> None:
    spectrum = fft_dft(samples)
    selection = select_first(spectrum, len(samples), SpectrumOrdering.INTERLEAVED)
    origin = Point2D(origin_x, origin_y)

    chain = build_epicycle_chain(selection, time, origin=origin)
    expected = complex(origin_x, origin_y) + reconstruct_at(selection, time)

    assert chain.centers == tuple(vector.start for vector in chain.vectors)
    assert all(
        current.start == previous.end
        for previous, current in pairwise(chain.vectors)
    )
    assert complex(chain.endpoint.x, chain.endpoint.y) == pytest.approx(expected, abs=ABS_TOL)


@given(
    complex_samples.filter(lambda values: len(values) >= 2),
    st.floats(min_value=-2.0, max_value=2.0, allow_nan=False, allow_infinity=False),
)
def test_permutation_changes_order_not_endpoint(
    samples: tuple[complex, ...],
    time: float,
) -> None:
    spectrum = fft_dft(samples)
    forward = tuple(coefficient.frequency for coefficient in spectrum.coefficients)
    left = select_frequencies(spectrum, forward)
    right = select_frequencies(spectrum, tuple(reversed(forward)))

    left_chain = build_epicycle_chain(left, time)
    right_chain = build_epicycle_chain(right, time)

    assert tuple(vector.frequency for vector in left_chain.vectors) == forward
    assert tuple(vector.frequency for vector in right_chain.vectors) == tuple(reversed(forward))
    assert np.allclose(
        complex(left_chain.endpoint.x, left_chain.endpoint.y),
        complex(right_chain.endpoint.x, right_chain.endpoint.y),
        atol=ABS_TOL,
        rtol=ABS_TOL,
    )


@given(
    complex_samples,
    st.floats(min_value=-2.0, max_value=2.0, allow_nan=False, allow_infinity=False),
)
def test_solo_active_set_endpoint_matches_selected_coefficient(
    samples: tuple[complex, ...],
    time: float,
) -> None:
    spectrum = fft_dft(samples)
    curve = Curve(tuple(Point2D(value.real, value.imag) for value in samples), closed=True)
    timeline = EpicycleTimeline(
        spectrum,
        curve,
        harmonic_count=len(samples),
        ordering=SpectrumOrdering.INTERLEAVED,
    )
    frequency = timeline.snapshot().selection.frequencies[len(samples) // 2]
    session = FrequencySoloSession()
    session.enter(timeline.snapshot(), frequency, source=timeline)
    timeline.play()
    projected = session.project(timeline.advance(abs(time)), source=timeline)

    expected = reconstruct_at(projected.selection, projected.chain.time)
    actual = complex(projected.chain.endpoint.x, projected.chain.endpoint.y)
    assert actual == pytest.approx(expected, abs=ABS_TOL)
    reconstructed = tuple(
        complex(point.x, point.y) for point in projected.reconstruction.points
    )
    assert reconstructed == pytest.approx(reconstruct_samples(projected.selection), abs=ABS_TOL)
    assert projected.trace[-1] == projected.chain.endpoint
