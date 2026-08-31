"""Dependency-free read-only projection for the desktop harmonic inspector."""

from dataclasses import dataclass

from fourier_sketch.domain import (
    CoefficientSelection,
    DomainValidationError,
    EpicycleChainState,
)


@dataclass(frozen=True, slots=True)
class HarmonicInspectorItem:
    """Canonical values displayed for one selected signed frequency."""

    selection_index: int
    frequency: int
    amplitude: float
    phase: float
    angular_velocity: float
    local_value: complex


def build_harmonic_inspector_item(
    selection: CoefficientSelection,
    chain: EpicycleChainState,
    frequency: int,
) -> HarmonicInspectorItem | None:
    """Return exact aligned coefficient/vector values or explicit stale-state empty."""

    if not isinstance(selection, CoefficientSelection):
        raise DomainValidationError("inspector selection must be a CoefficientSelection")
    if not isinstance(chain, EpicycleChainState):
        raise DomainValidationError("inspector chain must be an EpicycleChainState")
    if isinstance(frequency, bool) or not isinstance(frequency, int):
        raise DomainValidationError("inspector frequency must be an integer")
    if len(selection.coefficients) != len(chain.vectors):
        raise DomainValidationError("inspector selection and chain sizes must match")

    for index, (coefficient, vector) in enumerate(
        zip(selection.coefficients, chain.vectors, strict=True)
    ):
        if coefficient.frequency != vector.frequency:
            raise DomainValidationError("inspector frequency mapping must match")
        if coefficient.frequency == frequency:
            return HarmonicInspectorItem(
                selection_index=index,
                frequency=frequency,
                amplitude=vector.amplitude,
                phase=vector.phase,
                angular_velocity=vector.angular_velocity,
                local_value=vector.local_value,
            )
    return None
