"""Immutable coefficient-selection and reconstruction metric values."""

from dataclasses import dataclass
from enum import StrEnum

from ._validation import finite_float, immutable_tuple, integer
from .errors import DomainValidationError
from .fourier import FourierCoefficient, SpectrumOrdering


@dataclass(frozen=True, slots=True)
class CoefficientSelection:
    """An ordered non-empty subset of one canonical complete spectrum."""

    coefficients: tuple[FourierCoefficient, ...]
    sample_count: int
    ordering: SpectrumOrdering

    def __post_init__(self) -> None:
        coefficients = immutable_tuple(self.coefficients, field_name="coefficients")
        sample_count = integer(self.sample_count, field_name="sample_count")
        if sample_count <= 0:
            raise DomainValidationError("sample_count must be positive")
        if not coefficients:
            raise DomainValidationError("selection must contain at least one coefficient")
        if len(coefficients) > sample_count:
            raise DomainValidationError("selection cannot contain more than sample_count values")
        if any(not isinstance(item, FourierCoefficient) for item in coefficients):
            raise DomainValidationError("coefficients must be FourierCoefficient values")

        frequencies = tuple(item.frequency for item in coefficients)
        if len(frequencies) != len(set(frequencies)):
            raise DomainValidationError("selected coefficient frequencies must be unique")
        minimum_frequency = -(sample_count // 2)
        maximum_frequency = (sample_count - 1) // 2
        if any(
            frequency < minimum_frequency or frequency > maximum_frequency
            for frequency in frequencies
        ):
            raise DomainValidationError("selected frequencies must belong to the canonical set")
        if not isinstance(self.ordering, SpectrumOrdering):
            raise DomainValidationError("ordering must be a SpectrumOrdering")

        object.__setattr__(self, "coefficients", coefficients)
        object.__setattr__(self, "sample_count", sample_count)

    @property
    def frequencies(self) -> tuple[int, ...]:
        """Selected signed frequencies in evaluation order."""
        return tuple(coefficient.frequency for coefficient in self.coefficients)

    @property
    def coefficient_count(self) -> int:
        """Number of selected coefficients."""
        return len(self.coefficients)

    @property
    def is_full(self) -> bool:
        """Whether the selection contains every canonical bin."""
        return self.coefficient_count == self.sample_count


class NormalizedErrorStatus(StrEnum):
    """Defined states for the normalized reconstruction error."""

    DEFINED = "defined"
    ZERO_REFERENCE_EXACT = "zero_reference_exact"
    UNDEFINED_ZERO_REFERENCE = "undefined_zero_reference"


@dataclass(frozen=True, slots=True)
class ReconstructionMetrics:
    """Finite reconstruction errors plus an explicit normalized-error state."""

    mse: float
    rmse: float
    max_error: float
    normalized_error: float | None
    normalized_status: NormalizedErrorStatus

    def __post_init__(self) -> None:
        mse = finite_float(self.mse, field_name="mse")
        rmse = finite_float(self.rmse, field_name="rmse")
        max_error = finite_float(self.max_error, field_name="max_error")
        if mse < 0 or rmse < 0 or max_error < 0:
            raise DomainValidationError("reconstruction errors must be non-negative")
        if not isinstance(self.normalized_status, NormalizedErrorStatus):
            raise DomainValidationError("normalized_status must be a NormalizedErrorStatus")

        normalized_error = self.normalized_error
        if self.normalized_status is NormalizedErrorStatus.UNDEFINED_ZERO_REFERENCE:
            if normalized_error is not None:
                raise DomainValidationError("undefined normalized error must have no value")
        else:
            if normalized_error is None:
                raise DomainValidationError("defined normalized error must have a value")
            normalized_error = finite_float(
                normalized_error,
                field_name="normalized_error",
            )
            if normalized_error < 0:
                raise DomainValidationError("normalized_error must be non-negative")
            if (
                self.normalized_status is NormalizedErrorStatus.ZERO_REFERENCE_EXACT
                and normalized_error != 0.0
            ):
                raise DomainValidationError(
                    "exact zero-reference normalized error must equal zero"
                )

        object.__setattr__(self, "mse", mse)
        object.__setattr__(self, "rmse", rmse)
        object.__setattr__(self, "max_error", max_error)
        object.__setattr__(self, "normalized_error", normalized_error)
