"""Fourier transform of independent strokes with explicit pen-up jumps."""

from dataclasses import dataclass
from enum import StrEnum

from fourier_sketch.domain import (
    Curve,
    DomainValidationError,
    FourierSpectrum,
    PiecewiseCurve,
    SpectrumOrdering,
)
from fourier_sketch.math import (
    PiecewiseAllocation,
    PiecewiseBoundary,
    PiecewiseSampled,
    curve_to_complex_samples,
    fft_dft,
    resample_curve_by_arc_length,
    sample_piecewise_curve,
)

from .diagnostic_epicycles import EpicycleTimeline


class DiscontinuousMode(StrEnum):
    STRICT_TRAJECTORY = "strict_trajectory"
    PEN_UP_RENDERING = "pen_up_rendering"


@dataclass(frozen=True, slots=True)
class DiscontinuousFourierResult:
    sampled: PiecewiseSampled
    spectrum: FourierSpectrum
    timeline: EpicycleTimeline
    boundaries: tuple[PiecewiseBoundary, ...]
    mode: DiscontinuousMode

    @property
    def curve(self) -> PiecewiseCurve:
        return self.sampled.curve


@dataclass(frozen=True, slots=True)
class ForcedRouteFourierComparison:
    """Same-budget Fourier evidence for piecewise and forced-continuous policies."""

    discontinuous: DiscontinuousFourierResult
    forced_curve: Curve
    forced_spectrum: FourierSpectrum
    forced_timeline: EpicycleTimeline


def build_discontinuous_fourier(
    curve: PiecewiseCurve,
    sample_count: int,
    *,
    allocation: PiecewiseAllocation = PiecewiseAllocation.PROPORTIONAL,
    harmonic_count: int | None = None,
    mode: DiscontinuousMode = DiscontinuousMode.PEN_UP_RENDERING,
) -> DiscontinuousFourierResult:
    if not isinstance(mode, DiscontinuousMode):
        raise DomainValidationError("mode must be a DiscontinuousMode")
    sampled = sample_piecewise_curve(curve, sample_count, allocation=allocation)
    points = tuple(point for segment in sampled.curve.segments for point in segment.points)
    if len(points) < 2:
        raise DomainValidationError("discontinuous Fourier requires at least two samples")
    flattened = Curve(points)
    spectrum = fft_dft(curve_to_complex_samples(flattened))
    harmonics = min(15, spectrum.sample_count) if harmonic_count is None else harmonic_count
    timeline = EpicycleTimeline(
        spectrum,
        flattened,
        harmonic_count=harmonics,
        ordering=SpectrumOrdering.AMPLITUDE_DESCENDING,
    )
    return DiscontinuousFourierResult(sampled, spectrum, timeline, sampled.boundaries, mode)


def compare_discontinuous_with_forced_route(
    discontinuous: DiscontinuousFourierResult,
    forced_curve: Curve,
    *,
    harmonic_count: int | None = None,
) -> ForcedRouteFourierComparison:
    """Compare policies at one sample budget without converting one source into the other."""
    if not isinstance(discontinuous, DiscontinuousFourierResult):
        raise DomainValidationError("discontinuous result must be typed")
    if not isinstance(forced_curve, Curve) or not forced_curve.closed:
        raise DomainValidationError("forced route must be a closed Curve")
    sampled = resample_curve_by_arc_length(forced_curve, discontinuous.spectrum.sample_count)
    spectrum = fft_dft(curve_to_complex_samples(sampled))
    harmonics = discontinuous.timeline.harmonic_count if harmonic_count is None else harmonic_count
    timeline = EpicycleTimeline(
        spectrum,
        sampled,
        harmonic_count=harmonics,
        ordering=SpectrumOrdering.AMPLITUDE_DESCENDING,
    )
    return ForcedRouteFourierComparison(discontinuous, sampled, spectrum, timeline)
