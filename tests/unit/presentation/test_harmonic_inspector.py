"""Unit contracts for the dependency-free FS-024 inspector projection."""

from dataclasses import FrozenInstanceError
from math import cos, pi, sin

import pytest

from fourier_sketch.application import EpicycleFrame, build_freehand_timeline
from fourier_sketch.domain import CoefficientSelection, Curve, DomainValidationError, Point2D
from fourier_sketch.presentation.harmonic_inspector import (
    build_harmonic_inspector_item,
)


def _frame() -> EpicycleFrame:
    curve = Curve(
        tuple(
            Point2D(cos(2.0 * pi * index / 8), sin(2.0 * pi * index / 8))
            for index in range(8)
        ),
        closed=True,
    )
    return build_freehand_timeline(curve, harmonic_count=4).snapshot()


def test_projection_uses_the_exact_aligned_vector_for_stable_frequency() -> None:
    frame = _frame()
    frequency = frame.selection.frequencies[2]

    item = build_harmonic_inspector_item(frame.selection, frame.chain, frequency)

    assert item is not None
    vector = frame.chain.vectors[2]
    assert item.selection_index == 2
    assert item.frequency == frequency
    assert item.amplitude == vector.amplitude
    assert item.phase == vector.phase
    assert item.angular_velocity == vector.angular_velocity
    assert item.local_value == vector.local_value
    with pytest.raises(FrozenInstanceError):
        item.frequency = 99  # type: ignore[misc]


def test_stale_frequency_is_empty_and_inconsistent_mapping_fails_closed() -> None:
    frame = _frame()

    assert build_harmonic_inspector_item(frame.selection, frame.chain, 999) is None
    mismatched = CoefficientSelection(
        tuple(reversed(frame.selection.coefficients)),
        frame.selection.sample_count,
        frame.selection.ordering,
    )
    with pytest.raises(DomainValidationError, match="mapping"):
        build_harmonic_inspector_item(mismatched, frame.chain, 0)


def test_invalid_inputs_fail_closed() -> None:
    frame = _frame()
    with pytest.raises(DomainValidationError, match="frequency"):
        build_harmonic_inspector_item(frame.selection, frame.chain, True)
    with pytest.raises(DomainValidationError, match="selection"):
        build_harmonic_inspector_item(object(), frame.chain, 0)  # type: ignore[arg-type]
