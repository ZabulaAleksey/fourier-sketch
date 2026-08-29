"""Bounded, traceable spectrum and K-sweep analysis."""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from math import isfinite, log10

from fourier_sketch.domain import (
    CoefficientSelection,
    DomainValidationError,
    FourierSpectrum,
    ReconstructionMetrics,
    SpectrumOrdering,
)

from .metrics import reconstruction_metrics, retained_energy_ratio
from .reconstruction import MAX_RECONSTRUCTION_TERMS, reconstruct_samples
from .selection import select_first


class SpectrumAnalysisStatus(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"


@dataclass(frozen=True, slots=True)
class SpectrumPoint:
    frequency: int
    amplitude: float
    log_amplitude: float

    def __post_init__(self) -> None:
        if type(self.frequency) is not int:
            raise DomainValidationError("frequency must be an integer")
        if (
            isinstance(self.amplitude, bool)
            or not isinstance(self.amplitude, (int, float))
            or isinstance(self.log_amplitude, bool)
            or not isinstance(self.log_amplitude, (int, float))
        ):
            raise DomainValidationError("spectrum point values must be finite numbers")
        amplitude = float(self.amplitude)
        logarithm = float(self.log_amplitude)
        if not isfinite(amplitude) or amplitude < 0 or not isfinite(logarithm):
            raise DomainValidationError("spectrum point values must be finite and non-negative")
        object.__setattr__(self, "amplitude", amplitude)
        object.__setattr__(self, "log_amplitude", logarithm)


@dataclass(frozen=True, slots=True)
class KSweepPoint:
    k: int
    selection: CoefficientSelection
    retained_energy_ratio: float
    reconstruction_metrics: ReconstructionMetrics

    def __post_init__(self) -> None:
        if (
            type(self.k) is not int
            or self.k < 1
            or not isinstance(self.selection, CoefficientSelection)
        ):
            raise DomainValidationError("K sweep point must retain a valid selection")
        if self.selection.coefficient_count != self.k:
            raise DomainValidationError("K must match selection coefficient count")
        if isinstance(self.retained_energy_ratio, bool) or not isinstance(
            self.retained_energy_ratio, (int, float)
        ):
            raise DomainValidationError("retained energy ratio must be a finite number")
        ratio = float(self.retained_energy_ratio)
        if not isfinite(ratio) or not 0.0 <= ratio <= 1.0:
            raise DomainValidationError("retained energy ratio must be finite and bounded")
        if not isinstance(self.reconstruction_metrics, ReconstructionMetrics):
            raise DomainValidationError("K sweep point must retain reconstruction metrics")
        object.__setattr__(self, "retained_energy_ratio", ratio)


@dataclass(frozen=True, slots=True)
class SpectrumAnalysis:
    points: tuple[SpectrumPoint, ...]
    sweep: tuple[KSweepPoint, ...]
    ordering: SpectrumOrdering
    log_floor: float
    sample_count: int
    status: SpectrumAnalysisStatus = SpectrumAnalysisStatus.COMPLETE
    failure: str | None = None

    def __post_init__(self) -> None:
        try:
            points = tuple(self.points)
            sweep = tuple(self.sweep)
        except TypeError as error:
            raise DomainValidationError("spectrum analysis collections must be iterable") from error
        if (
            type(self.sample_count) is not int
            or self.sample_count < 1
            or not points
            or len(points) != self.sample_count
            or any(not isinstance(point, SpectrumPoint) for point in points)
            or any(not isinstance(point, KSweepPoint) for point in sweep)
            or len({point.frequency for point in points}) != len(points)
            or tuple(point.k for point in sweep) != tuple(sorted({point.k for point in sweep}))
            or any(point.selection.sample_count != self.sample_count for point in sweep)
        ):
            raise DomainValidationError("spectrum analysis shape is invalid")
        if (
            not isinstance(self.ordering, SpectrumOrdering)
            or self.ordering is SpectrumOrdering.EXPLICIT
        ):
            raise DomainValidationError("spectrum analysis ordering is invalid")
        if isinstance(self.log_floor, bool) or not isinstance(self.log_floor, (int, float)):
            raise DomainValidationError("spectrum analysis log floor must be a finite number")
        floor = float(self.log_floor)
        if not isfinite(floor) or floor <= 0:
            raise DomainValidationError("spectrum analysis log floor must be positive and finite")
        if not isinstance(self.status, SpectrumAnalysisStatus):
            raise DomainValidationError("spectrum analysis status is invalid")
        if (self.status is SpectrumAnalysisStatus.COMPLETE) != (self.failure is None):
            raise DomainValidationError("spectrum analysis failure must match status")
        if self.failure is not None and (not isinstance(self.failure, str) or not self.failure):
            raise DomainValidationError("spectrum analysis failure must be a stable string")
        object.__setattr__(self, "points", points)
        object.__setattr__(self, "sweep", sweep)
        object.__setattr__(self, "log_floor", floor)


def analyze_spectrum(
    spectrum: FourierSpectrum,
    samples: Sequence[complex],
    k_values: Sequence[int],
    *,
    ordering: SpectrumOrdering = SpectrumOrdering.AMPLITUDE_DESCENDING,
    log_floor: float = 1e-12,
) -> SpectrumAnalysis:
    """Return finite amplitude views and measured reconstruction evidence."""
    if not isinstance(spectrum, FourierSpectrum):
        raise DomainValidationError("spectrum must be a FourierSpectrum")
    if not isinstance(ordering, SpectrumOrdering) or ordering is SpectrumOrdering.EXPLICIT:
        raise DomainValidationError("ordering must be one supported non-explicit SpectrumOrdering")
    if isinstance(log_floor, bool) or not isinstance(log_floor, (int, float)):
        raise DomainValidationError("log_floor must be a positive finite number")
    floor = float(log_floor)
    if not isfinite(floor) or floor <= 0:
        raise DomainValidationError("log_floor must be a positive finite number")
    try:
        source = tuple(samples)
    except TypeError as error:
        raise DomainValidationError("samples must be an iterable") from error
    if len(source) != spectrum.sample_count:
        raise DomainValidationError("samples must match spectrum sample_count")
    if any(
        not isinstance(value, complex)
        or not isfinite(value.real)
        or not isfinite(value.imag)
        for value in source
    ):
        raise DomainValidationError("samples must contain finite complex values")
    try:
        ks = tuple(k_values)
    except TypeError as error:
        raise DomainValidationError("k_values must be an iterable") from error
    if not ks or any(isinstance(k, bool) or not isinstance(k, int) for k in ks):
        raise DomainValidationError("k_values must contain positive integers")
    if ks != tuple(sorted(set(ks))) or any(k < 1 or k > spectrum.sample_count for k in ks):
        raise DomainValidationError("k_values must be unique, ascending and bounded")
    ordered = tuple(sorted(spectrum.coefficients, key=lambda c: c.frequency))
    view = tuple(
        SpectrumPoint(c.frequency, c.amplitude, log10(max(c.amplitude, floor)))
        for c in ordered
    )
    sweep: list[KSweepPoint] = []
    for k in ks:
        if len(source) * k > MAX_RECONSTRUCTION_TERMS:
            return SpectrumAnalysis(
                view,
                tuple(sweep),
                ordering,
                floor,
                spectrum.sample_count,
                SpectrumAnalysisStatus.PARTIAL,
                "reconstruction_budget",
            )
        selection = select_first(spectrum, k, ordering)
        reconstructed = reconstruct_samples(selection, sample_count=len(source))
        sweep.append(
            KSweepPoint(
                k,
                selection,
                retained_energy_ratio(selection, spectrum),
                reconstruction_metrics(source, reconstructed),
            )
        )
    return SpectrumAnalysis(view, tuple(sweep), ordering, floor, spectrum.sample_count)
