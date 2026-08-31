"""Bounded deterministic first-K analysis over an immutable timeline baseline."""

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite

from fourier_sketch.domain import (
    CoefficientSelection,
    Curve,
    DomainValidationError,
    EpicycleChainState,
    FourierSpectrum,
    ReconstructionMetrics,
    SpectrumOrdering,
)
from fourier_sketch.math import (
    build_epicycle_chain,
    complex_samples_to_curve,
    reconstruct_samples,
    reconstruction_metrics,
    retained_energy_ratio,
    select_first,
)

from .diagnostic_epicycles import MAX_INTERACTIVE_HARMONICS, EpicycleFrame

MIN_BUILD_UP_DWELL_SECONDS = 0.10
MAX_BUILD_UP_DWELL_SECONDS = 5.00
DEFAULT_BUILD_UP_DWELL_SECONDS = 0.50


class BuildUpState(StrEnum):
    """Lifecycle of the discrete first-K sequence."""

    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"


@dataclass(frozen=True, slots=True)
class BuildUpMetrics:
    """Measured values for exactly the active first-K selection."""

    current_count: int
    target_count: int
    latest_frequency: int
    retained_energy_ratio: float
    reconstruction_metrics: ReconstructionMetrics


@dataclass(frozen=True, slots=True)
class BuildUpSnapshot:
    """Immutable display/provenance state emitted by the build-up session."""

    frame: EpicycleFrame
    state: BuildUpState
    ordering: SpectrumOrdering
    dwell_seconds: float
    metrics: BuildUpMetrics


class HarmonicBuildUpSession:
    """Advance one visible deterministic K step per bounded dwell transition."""

    def __init__(self) -> None:
        self._reset()

    def _reset(self) -> None:
        self._source: object | None = None
        self._original: Curve | None = None
        self._spectrum: FourierSpectrum | None = None
        self._ordering: SpectrumOrdering | None = None
        self._target_count = 0
        self._current_count = 0
        self._dwell_seconds = 0.0
        self._elapsed_seconds = 0.0
        self._state: BuildUpState | None = None
        self._selection: CoefficientSelection | None = None
        self._reconstruction: Curve | None = None
        self._metrics: BuildUpMetrics | None = None
        self._prepared_count = 0

    @property
    def active(self) -> bool:
        return self._source is not None

    @property
    def state(self) -> BuildUpState | None:
        return self._state

    @property
    def current_count(self) -> int:
        return self._current_count

    @property
    def target_count(self) -> int:
        return self._target_count

    def enter(
        self,
        frame: EpicycleFrame,
        *,
        spectrum: FourierSpectrum,
        source: object,
        ordering: SpectrumOrdering,
        target_count: int,
        dwell_seconds: float = DEFAULT_BUILD_UP_DWELL_SECONDS,
    ) -> BuildUpSnapshot:
        """Start at K=1 transactionally and leave every baseline value untouched."""

        if self.active:
            raise DomainValidationError("harmonic Build-Up is already active")
        self._validate_contract(frame, spectrum, source, ordering, target_count, dwell_seconds)
        selection, reconstruction, metrics = self._prepare(
            frame,
            spectrum,
            ordering,
            1,
            target_count,
        )
        state = BuildUpState.COMPLETED if target_count == 1 else BuildUpState.RUNNING
        snapshot = self._make_snapshot(
            frame,
            selection,
            reconstruction,
            metrics,
            state,
            ordering,
            float(dwell_seconds),
        )
        self._source = source
        self._original = frame.original
        self._spectrum = spectrum
        self._ordering = ordering
        self._target_count = target_count
        self._current_count = 1
        self._dwell_seconds = float(dwell_seconds)
        self._elapsed_seconds = 0.0
        self._state = state
        self._selection = selection
        self._reconstruction = reconstruction
        self._metrics = metrics
        self._prepared_count = 1
        return snapshot

    def play(self) -> None:
        if not self.active:
            raise DomainValidationError("harmonic Build-Up is not active")
        if self._state is BuildUpState.PAUSED:
            self._state = BuildUpState.RUNNING

    def pause(self) -> None:
        if not self.active:
            raise DomainValidationError("harmonic Build-Up is not active")
        if self._state is BuildUpState.RUNNING:
            self._state = BuildUpState.PAUSED

    def restart(self) -> None:
        if not self.active:
            raise DomainValidationError("harmonic Build-Up is not active")
        self._current_count = 1
        self._elapsed_seconds = 0.0
        self._state = BuildUpState.PAUSED
        self._prepared_count = 0

    def advance(self, delta_seconds: float) -> None:
        delta = self._validate_delta(delta_seconds)
        if not self.active:
            raise DomainValidationError("harmonic Build-Up is not active")
        if self._state is not BuildUpState.RUNNING or delta == 0.0:
            return
        next_elapsed = self._elapsed_seconds + delta
        if not isfinite(next_elapsed):
            raise DomainValidationError("Build-Up dwell accumulator must remain finite")
        if next_elapsed < self._dwell_seconds:
            self._elapsed_seconds = next_elapsed
            return
        self._current_count += 1
        self._elapsed_seconds = 0.0
        self._prepared_count = 0
        if self._current_count >= self._target_count:
            self._current_count = self._target_count
            self._state = BuildUpState.COMPLETED

    def project(self, frame: EpicycleFrame, *, source: object) -> BuildUpSnapshot | None:
        """Return the current first-K display state or clear mismatched provenance."""

        if not self.active:
            return None
        if source is not self._source or frame.original is not self._original:
            self.clear()
            return None
        spectrum = self._spectrum
        ordering = self._ordering
        state = self._state
        if spectrum is None or ordering is None or state is None:
            self.clear()
            return None
        if self._prepared_count != self._current_count:
            selection, reconstruction, metrics = self._prepare(
                frame,
                spectrum,
                ordering,
                self._current_count,
                self._target_count,
            )
        else:
            cached_selection = self._selection
            cached_reconstruction = self._reconstruction
            cached_metrics = self._metrics
            if (
                cached_selection is None
                or cached_reconstruction is None
                or cached_metrics is None
            ):
                self.clear()
                return None
            selection = cached_selection
            reconstruction = cached_reconstruction
            metrics = cached_metrics
        snapshot = self._make_snapshot(
            frame,
            selection,
            reconstruction,
            metrics,
            state,
            ordering,
            self._dwell_seconds,
        )
        self._selection = selection
        self._reconstruction = reconstruction
        self._metrics = metrics
        self._prepared_count = self._current_count
        return snapshot

    def exit(self, frame: EpicycleFrame, *, source: object) -> EpicycleFrame:
        if not self.active:
            raise DomainValidationError("harmonic Build-Up is not active")
        if source is not self._source:
            raise DomainValidationError("harmonic Build-Up source does not match")
        self.clear()
        return frame

    def clear(self) -> None:
        self._reset()

    @staticmethod
    def _validate_contract(
        frame: EpicycleFrame,
        spectrum: FourierSpectrum,
        source: object,
        ordering: SpectrumOrdering,
        target_count: int,
        dwell_seconds: float,
    ) -> None:
        if not isinstance(frame, EpicycleFrame):
            raise DomainValidationError("Build-Up requires an EpicycleFrame")
        if not isinstance(spectrum, FourierSpectrum):
            raise DomainValidationError("Build-Up requires a FourierSpectrum")
        if source is None:
            raise DomainValidationError("Build-Up requires a source owner")
        if frame.original.sample_count != spectrum.sample_count:
            raise DomainValidationError("Build-Up frame and spectrum sample_count must match")
        spectrum_by_frequency = {
            coefficient.frequency: coefficient for coefficient in spectrum.coefficients
        }
        if any(
            spectrum_by_frequency.get(coefficient.frequency) != coefficient
            for coefficient in frame.selection.coefficients
        ):
            raise DomainValidationError("Build-Up spectrum does not own the baseline selection")
        if not isinstance(ordering, SpectrumOrdering) or ordering is SpectrumOrdering.EXPLICIT:
            raise DomainValidationError("Build-Up ordering must be non-explicit")
        maximum = min(spectrum.sample_count, MAX_INTERACTIVE_HARMONICS)
        if isinstance(target_count, bool) or not isinstance(target_count, int):
            raise DomainValidationError("Build-Up target_count must be an integer")
        if target_count < 1 or target_count > maximum:
            raise DomainValidationError(f"Build-Up target_count must be between 1 and {maximum}")
        HarmonicBuildUpSession._validate_dwell(dwell_seconds)

    @staticmethod
    def _validate_dwell(value: float) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise DomainValidationError("Build-Up dwell_seconds must be a finite real number")
        normalized = float(value)
        if (
            not isfinite(normalized)
            or normalized < MIN_BUILD_UP_DWELL_SECONDS
            or normalized > MAX_BUILD_UP_DWELL_SECONDS
        ):
            raise DomainValidationError(
                "Build-Up dwell_seconds must be between "
                f"{MIN_BUILD_UP_DWELL_SECONDS} and {MAX_BUILD_UP_DWELL_SECONDS}"
            )
        return normalized

    @staticmethod
    def _validate_delta(value: float) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise DomainValidationError("Build-Up delta_seconds must be a finite real number")
        normalized = float(value)
        if not isfinite(normalized) or normalized < 0.0:
            raise DomainValidationError("Build-Up delta_seconds must be finite and non-negative")
        return normalized

    @staticmethod
    def _prepare(
        frame: EpicycleFrame,
        spectrum: FourierSpectrum,
        ordering: SpectrumOrdering,
        count: int,
        target_count: int,
    ) -> tuple[CoefficientSelection, Curve, BuildUpMetrics]:
        selection = select_first(spectrum, count, ordering)
        samples = reconstruct_samples(selection)
        origin = complex(frame.chain.origin.x, frame.chain.origin.y)
        display_samples = tuple(sample + origin for sample in samples)
        reconstruction = complex_samples_to_curve(
            display_samples,
            closed=frame.original.closed,
        )
        reference = tuple(complex(point.x, point.y) for point in frame.original.points)
        metrics = BuildUpMetrics(
            current_count=count,
            target_count=target_count,
            latest_frequency=selection.frequencies[-1],
            retained_energy_ratio=retained_energy_ratio(selection, spectrum),
            reconstruction_metrics=reconstruction_metrics(reference, display_samples),
        )
        return selection, reconstruction, metrics

    @staticmethod
    def _make_snapshot(
        frame: EpicycleFrame,
        selection: CoefficientSelection,
        reconstruction: Curve,
        metrics: BuildUpMetrics,
        state: BuildUpState,
        ordering: SpectrumOrdering,
        dwell_seconds: float,
    ) -> BuildUpSnapshot:
        chain: EpicycleChainState = build_epicycle_chain(
            selection,
            frame.chain.time,
            origin=frame.chain.origin,
        )
        display = EpicycleFrame(
            chain=chain,
            trace=(chain.endpoint,),
            visibility=frame.visibility,
            selection=selection,
            original=frame.original,
            reconstruction=reconstruction,
            timeline_state=frame.timeline_state,
            speed=frame.speed,
        )
        return BuildUpSnapshot(display, state, ordering, dwell_seconds, metrics)
