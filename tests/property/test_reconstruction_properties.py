"""Generated contracts for selection, reconstruction and energy."""

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from fourier_sketch.domain import NormalizedErrorStatus, SpectrumOrdering
from fourier_sketch.math import (
    fft_dft,
    reconstruct_samples,
    reconstruction_metrics,
    retained_energy_ratio,
    select_first,
)

pytestmark = pytest.mark.property

ABS_TOL = 1e-10  # N<=8 generated integer samples; direct Fourier sum accumulates O(N*eps).

finite_component = st.integers(min_value=-20, max_value=20).map(float)
complex_samples = st.lists(
    st.builds(complex, finite_component, finite_component),
    min_size=1,
    max_size=8,
).map(tuple)


@given(complex_samples)
def test_full_selection_reconstructs_same_samples_for_every_ordering(
    samples: tuple[complex, ...],
) -> None:
    spectrum = fft_dft(samples)

    for ordering in (
        SpectrumOrdering.SIGNED,
        SpectrumOrdering.ABSOLUTE_FREQUENCY,
        SpectrumOrdering.AMPLITUDE_DESCENDING,
        SpectrumOrdering.INTERLEAVED,
    ):
        selection = select_first(spectrum, len(samples), ordering)
        reconstructed = reconstruct_samples(selection)

        assert np.allclose(reconstructed, samples, atol=ABS_TOL, rtol=ABS_TOL)
        metrics = reconstruction_metrics(samples, reconstructed)
        assert metrics.normalized_status in (
            NormalizedErrorStatus.DEFINED,
            NormalizedErrorStatus.ZERO_REFERENCE_EXACT,
        )
        assert retained_energy_ratio(selection, spectrum) == 1.0


@given(complex_samples, st.data())
def test_partial_selection_is_unique_and_retains_bounded_energy(
    samples: tuple[complex, ...],
    data: st.DataObject,
) -> None:
    spectrum = fft_dft(samples)
    count = data.draw(st.integers(min_value=1, max_value=len(samples)))
    selection = select_first(spectrum, count, SpectrumOrdering.AMPLITUDE_DESCENDING)

    assert len(selection.frequencies) == count
    assert len(set(selection.frequencies)) == count
    assert 0.0 <= retained_energy_ratio(selection, spectrum) <= 1.0
