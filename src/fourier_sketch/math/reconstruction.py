"""Continuous and sample-grid reconstruction from explicit coefficient selections."""

from cmath import exp
from math import pi

from fourier_sketch.domain import CoefficientSelection, DomainValidationError

from ._inverse import inverse_grid
from ._validation import finite_complex_value

MAX_RECONSTRUCTION_SAMPLES = 262_144
MAX_RECONSTRUCTION_TERMS = 16_777_216


def reconstruct_at(selection: CoefficientSelection, time: float) -> complex:
    """Evaluate the selected periodic Fourier sum at normalized time ``time``."""
    _require_selection(selection)
    if isinstance(time, bool) or not isinstance(time, (int, float)):
        raise DomainValidationError("time must be a finite real number")
    try:
        normalized_time = float(time)
    except OverflowError as error:
        raise DomainValidationError("time must be finite") from error
    if not (-float("inf") < normalized_time < float("inf")):
        raise DomainValidationError("time must be finite")
    periodic_time = normalized_time % 1.0
    value = sum(
        coefficient.value
        * exp(2j * pi * coefficient.frequency * periodic_time)
        for coefficient in selection.coefficients
    )
    return finite_complex_value(value, field_name="reconstruction")


def reconstruct_samples(
    selection: CoefficientSelection,
    *,
    sample_count: int | None = None,
) -> tuple[complex, ...]:
    """Evaluate a selection on an evenly spaced periodic sample grid."""
    _require_selection(selection)
    output_count = selection.sample_count if sample_count is None else sample_count
    if isinstance(output_count, bool) or not isinstance(output_count, int):
        raise DomainValidationError("sample_count must be an integer")
    if output_count <= 0:
        raise DomainValidationError("sample_count must be positive")
    if output_count > MAX_RECONSTRUCTION_SAMPLES:
        raise DomainValidationError(
            f"sample_count must not exceed {MAX_RECONSTRUCTION_SAMPLES}"
        )
    term_count = output_count * selection.coefficient_count
    if term_count > MAX_RECONSTRUCTION_TERMS:
        raise DomainValidationError(
            f"reconstruction must not exceed {MAX_RECONSTRUCTION_TERMS} evaluated terms"
        )
    return inverse_grid(
        selection.coefficients,
        output_count=output_count,
    )


def _require_selection(selection: CoefficientSelection) -> None:
    if not isinstance(selection, CoefficientSelection):
        raise DomainValidationError("selection must be a CoefficientSelection")
