"""Bounded transactional authoring of explicit Fourier harmonic sets."""

from collections.abc import Iterable

from fourier_sketch.domain import (
    DomainValidationError,
    FourierCoefficient,
    FourierSpectrum,
    ManualHarmonic,
    SpectrumOrdering,
)
from fourier_sketch.math import complex_samples_to_curve, idft, signed_frequencies

from .diagnostic_epicycles import EpicycleTimeline

PLAYGROUND_MAX_COMPONENTS = 16
PLAYGROUND_MAX_TOTAL_AMPLITUDE = 8.0
PLAYGROUND_SAMPLE_COUNT = 128


class HarmonicPlaygroundSession:
    """Own an ordered candidate set without mutating any normal desktop timeline."""

    def __init__(self, components: Iterable[ManualHarmonic] | None = None) -> None:
        initial = (
            (ManualHarmonic(frequency=1, amplitude=1.0, phase=0.0),)
            if components is None
            else tuple(components)
        )
        self._components = self._validated_components(initial, allow_empty=True)

    @property
    def components(self) -> tuple[ManualHarmonic, ...]:
        return self._components

    def upsert(self, component: ManualHarmonic) -> tuple[ManualHarmonic, ...]:
        """Atomically replace one frequency in place or append a new row."""

        if not isinstance(component, ManualHarmonic):
            raise DomainValidationError("component must be a ManualHarmonic")
        candidate = list(self._components)
        for index, current in enumerate(candidate):
            if current.frequency == component.frequency:
                candidate[index] = component
                break
        else:
            candidate.append(component)
        validated = self._validated_components(tuple(candidate))
        self._components = validated
        return validated

    def remove(self, frequency: int) -> tuple[ManualHarmonic, ...]:
        candidate = tuple(
            component
            for component in self._components
            if component.frequency != frequency
        )
        if len(candidate) == len(self._components):
            raise DomainValidationError("harmonic frequency is not present")
        self._components = self._validated_components(candidate, allow_empty=True)
        return self._components

    def clear(self) -> tuple[ManualHarmonic, ...]:
        self._components = ()
        return self._components

    def reset_circle(self) -> tuple[ManualHarmonic, ...]:
        self._components = (ManualHarmonic(frequency=1, amplitude=1.0, phase=0.0),)
        return self._components

    def build_timeline(self, *, speed: float = 1.0) -> EpicycleTimeline:
        """Build an actual explicit-order Fourier timeline at paused t=0."""

        components = self._validated_components(self._components)
        by_frequency = {component.frequency: component for component in components}
        spectrum = FourierSpectrum(
            coefficients=tuple(
                FourierCoefficient(
                    frequency=frequency,
                    value=(
                        by_frequency[frequency].value
                        if frequency in by_frequency
                        else 0j
                    ),
                )
                for frequency in signed_frequencies(PLAYGROUND_SAMPLE_COUNT)
            ),
            sample_count=PLAYGROUND_SAMPLE_COUNT,
            source_metadata=(
                ("source", "harmonic_playground"),
                ("component_count", str(len(components))),
            ),
        )
        generated_curve = complex_samples_to_curve(idft(spectrum), closed=True)
        return EpicycleTimeline(
            spectrum,
            generated_curve,
            harmonic_count=len(components),
            ordering=SpectrumOrdering.EXPLICIT,
            explicit_frequencies=tuple(component.frequency for component in components),
            speed=speed,
        )

    @staticmethod
    def _validated_components(
        components: tuple[ManualHarmonic, ...],
        *,
        allow_empty: bool = False,
    ) -> tuple[ManualHarmonic, ...]:
        if not allow_empty and not components:
            raise DomainValidationError("playground requires at least one harmonic")
        if len(components) > PLAYGROUND_MAX_COMPONENTS:
            raise DomainValidationError(
                f"playground must not exceed {PLAYGROUND_MAX_COMPONENTS} harmonics"
            )
        if any(not isinstance(component, ManualHarmonic) for component in components):
            raise DomainValidationError("playground components must be ManualHarmonic values")
        frequencies = tuple(component.frequency for component in components)
        if len(frequencies) != len(set(frequencies)):
            raise DomainValidationError("playground harmonic frequencies must be unique")
        if sum(component.amplitude for component in components) > PLAYGROUND_MAX_TOTAL_AMPLITUDE:
            raise DomainValidationError(
                f"playground total amplitude must not exceed "
                f"{PLAYGROUND_MAX_TOTAL_AMPLITUDE}"
            )
        return components
