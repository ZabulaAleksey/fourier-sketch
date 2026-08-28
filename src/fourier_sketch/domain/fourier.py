"""Fourier coefficient and spectrum domain values."""

from cmath import phase as complex_phase
from dataclasses import dataclass
from enum import StrEnum
from math import hypot, isfinite

from ._validation import finite_complex, immutable_tuple, integer
from .errors import DomainValidationError


class FourierNormalization(StrEnum):
    """Supported normalization contract for the one-dimensional curve transform."""

    FORWARD_1_OVER_N = "forward_1_over_n"


class FrequencyConvention(StrEnum):
    """Supported frequency-label convention."""

    SIGNED = "signed"


class SpectrumOrdering(StrEnum):
    """Deterministic views over one complete Fourier spectrum."""

    SIGNED = "signed"
    ABSOLUTE_FREQUENCY = "absolute_frequency"
    AMPLITUDE_DESCENDING = "amplitude_descending"
    INTERLEAVED = "interleaved"
    EXPLICIT = "explicit"


@dataclass(frozen=True, slots=True)
class FourierCoefficient:
    """A signed-frequency complex Fourier coefficient."""

    frequency: int
    value: complex

    def __post_init__(self) -> None:
        object.__setattr__(self, "frequency", integer(self.frequency, field_name="frequency"))
        object.__setattr__(self, "value", finite_complex(self.value, field_name="value"))

    @property
    def real(self) -> float:
        """Real component of the complex coefficient."""
        return self.value.real

    @property
    def imaginary(self) -> float:
        """Imaginary component of the complex coefficient."""
        return self.value.imag

    @property
    def amplitude(self) -> float:
        """Magnitude of the coefficient."""
        magnitude = hypot(self.value.real, self.value.imag)
        if not isfinite(magnitude):
            raise DomainValidationError("coefficient amplitude must be finite")
        return magnitude

    @property
    def phase(self) -> float:
        """Principal phase, with a stable zero convention for a zero coefficient."""
        if self.value == 0:
            return 0.0
        return complex_phase(self.value)


@dataclass(frozen=True, slots=True)
class FourierSpectrum:
    """A complete immutable spectrum for a finite sample sequence."""

    coefficients: tuple[FourierCoefficient, ...]
    sample_count: int
    normalization: FourierNormalization = FourierNormalization.FORWARD_1_OVER_N
    frequency_convention: FrequencyConvention = FrequencyConvention.SIGNED
    source_metadata: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        coefficients = immutable_tuple(self.coefficients, field_name="coefficients")
        sample_count = integer(self.sample_count, field_name="sample_count")

        if sample_count <= 0:
            raise DomainValidationError("sample_count must be positive")
        if len(coefficients) != sample_count:
            raise DomainValidationError(
                "a complete spectrum must contain sample_count coefficients"
            )
        if any(not isinstance(item, FourierCoefficient) for item in coefficients):
            raise DomainValidationError("coefficients must be FourierCoefficient values")

        frequencies = tuple(item.frequency for item in coefficients)
        if len(frequencies) != len(set(frequencies)):
            raise DomainValidationError("coefficient frequencies must be unique")
        expected_frequencies = {
            index if index <= (sample_count - 1) // 2 else index - sample_count
            for index in range(sample_count)
        }
        if set(frequencies) != expected_frequencies:
            raise DomainValidationError(
                "a complete signed spectrum must contain the canonical frequency set"
            )
        if not isinstance(self.normalization, FourierNormalization):
            raise DomainValidationError("normalization must be a FourierNormalization")
        if not isinstance(self.frequency_convention, FrequencyConvention):
            raise DomainValidationError("frequency_convention must be a FrequencyConvention")

        metadata = self._validated_metadata(self.source_metadata)
        object.__setattr__(self, "coefficients", coefficients)
        object.__setattr__(self, "sample_count", sample_count)
        object.__setattr__(self, "source_metadata", metadata)

    @staticmethod
    def _validated_metadata(
        source_metadata: tuple[tuple[str, str], ...],
    ) -> tuple[tuple[str, str], ...]:
        metadata = immutable_tuple(source_metadata, field_name="source_metadata")
        normalized: list[tuple[str, str]] = []
        seen_keys: set[str] = set()

        for item in metadata:
            if not isinstance(item, tuple) or len(item) != 2:
                raise DomainValidationError("source_metadata entries must be (key, value) pairs")
            key, value = item
            if not isinstance(key, str) or not key:
                raise DomainValidationError("source_metadata keys must be non-empty strings")
            if not isinstance(value, str):
                raise DomainValidationError("source_metadata values must be strings")
            if key in seen_keys:
                raise DomainValidationError("source_metadata keys must be unique")
            seen_keys.add(key)
            normalized.append((key, value))

        return tuple(normalized)
