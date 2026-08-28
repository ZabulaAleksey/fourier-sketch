"""Application timeline that composes accepted Fourier and epicycle contracts."""

from dataclasses import dataclass, replace
from enum import StrEnum
from math import isfinite

from fourier_sketch.domain import (
    CoefficientSelection,
    Curve,
    DomainValidationError,
    EpicycleChainState,
    FourierSpectrum,
    Point2D,
    SpectrumOrdering,
)
from fourier_sketch.math import (
    build_epicycle_chain,
    complex_samples_to_curve,
    reconstruct_samples,
    select_first,
)

MAX_INTERACTIVE_HARMONICS = 4096
MAX_TRACE_POINTS = 10_000
MAX_SPEED = 100.0


class TimelineState(StrEnum):
    """Explicit animation lifecycle for the diagnostic controller."""

    PAUSED = "paused"
    RUNNING = "running"


@dataclass(frozen=True, slots=True)
class RenderVisibility:
    """Presentation-only layer visibility; never part of mathematical state."""

    circles: bool = True
    vectors: bool = True
    endpoint: bool = True
    trace: bool = True
    original: bool = True
    reconstruction: bool = True

    def __post_init__(self) -> None:
        if any(
            not isinstance(value, bool)
            for value in (
                self.circles,
                self.vectors,
                self.endpoint,
                self.trace,
                self.original,
                self.reconstruction,
            )
        ):
            raise DomainValidationError("visibility values must be booleans")


@dataclass(frozen=True, slots=True)
class EpicycleFrame:
    """Immutable renderer input assembled by the application timeline."""

    chain: EpicycleChainState
    trace: tuple[Point2D, ...]
    visibility: RenderVisibility
    selection: CoefficientSelection
    original: Curve
    reconstruction: Curve
    timeline_state: TimelineState
    speed: float

    def __post_init__(self) -> None:
        if not isinstance(self.chain, EpicycleChainState):
            raise DomainValidationError("frame chain must be an EpicycleChainState")
        if not isinstance(self.visibility, RenderVisibility):
            raise DomainValidationError("frame visibility must be a RenderVisibility")
        if not isinstance(self.selection, CoefficientSelection):
            raise DomainValidationError("frame selection must be a CoefficientSelection")
        if not isinstance(self.original, Curve) or not isinstance(self.reconstruction, Curve):
            raise DomainValidationError("frame overlays must be Curve values")
        try:
            trace = tuple(self.trace)
        except TypeError as error:
            raise DomainValidationError("frame trace must be an iterable collection") from error
        if not trace:
            raise DomainValidationError("frame trace must contain at least one endpoint")
        if len(trace) > MAX_TRACE_POINTS:
            raise DomainValidationError(f"frame trace must not exceed {MAX_TRACE_POINTS} points")
        if any(not isinstance(point, Point2D) for point in trace):
            raise DomainValidationError("frame trace must contain Point2D values")
        if trace[-1] != self.chain.endpoint:
            raise DomainValidationError("the latest trace point must equal the chain endpoint")
        if not isinstance(self.timeline_state, TimelineState):
            raise DomainValidationError("timeline_state must be a TimelineState")
        if tuple(vector.frequency for vector in self.chain.vectors) != self.selection.frequencies:
            raise DomainValidationError("frame chain must preserve selection frequency order")
        if (
            self.original.sample_count != self.selection.sample_count
            or self.reconstruction.sample_count != self.selection.sample_count
        ):
            raise DomainValidationError("frame curves and selection sample_count must match")
        object.__setattr__(self, "trace", trace)
        object.__setattr__(self, "speed", validate_timeline_speed(self.speed))


class EpicycleTimeline:
    """Validated mutable controller; every emitted frame remains immutable."""

    def __init__(
        self,
        spectrum: FourierSpectrum,
        original: Curve,
        *,
        harmonic_count: int,
        ordering: SpectrumOrdering = SpectrumOrdering.AMPLITUDE_DESCENDING,
        speed: float = 1.0,
        visibility: RenderVisibility | None = None,
    ) -> None:
        if not isinstance(spectrum, FourierSpectrum):
            raise DomainValidationError("spectrum must be a FourierSpectrum")
        if not isinstance(original, Curve):
            raise DomainValidationError("original must be a Curve")
        if original.sample_count != spectrum.sample_count:
            raise DomainValidationError("original and spectrum sample_count must match")
        if not isinstance(ordering, SpectrumOrdering) or ordering is SpectrumOrdering.EXPLICIT:
            raise DomainValidationError("timeline ordering must be a non-explicit SpectrumOrdering")

        self._spectrum = spectrum
        self._original = original
        self._ordering = ordering
        self._visibility = visibility or RenderVisibility()
        self._state = TimelineState.PAUSED
        self._time = 0.0
        self._speed = validate_timeline_speed(speed)
        self._selection = self._make_selection(harmonic_count)
        self._reconstruction = self._make_reconstruction()
        self._chain = build_epicycle_chain(self._selection, self._time)
        self._trace = [self._chain.endpoint]

    @property
    def state(self) -> TimelineState:
        return self._state

    @property
    def harmonic_count(self) -> int:
        return self._selection.coefficient_count

    @property
    def speed(self) -> float:
        return self._speed

    @property
    def maximum_harmonics(self) -> int:
        return min(self._spectrum.sample_count, MAX_INTERACTIVE_HARMONICS)

    @property
    def maximum_speed(self) -> float:
        return MAX_SPEED

    def snapshot(self) -> EpicycleFrame:
        """Return current state without advancing time or appending trace."""
        return self._frame()

    def play(self) -> EpicycleFrame:
        self._state = TimelineState.RUNNING
        return self._frame()

    def pause(self) -> EpicycleFrame:
        self._state = TimelineState.PAUSED
        return self._frame()

    def restart(self) -> EpicycleFrame:
        """Pause at zero and replace history with exactly the new zero-time endpoint."""
        chain = build_epicycle_chain(self._selection, 0.0)
        self._state = TimelineState.PAUSED
        self._time = 0.0
        self._chain = chain
        self._trace = [self._chain.endpoint]
        return self._frame()

    def advance(self, delta_seconds: float) -> EpicycleFrame:
        delta = _validated_delta(delta_seconds)
        if self._state is TimelineState.PAUSED or delta == 0.0:
            return self._frame()
        if len(self._trace) >= MAX_TRACE_POINTS:
            raise DomainValidationError(f"trace must not exceed {MAX_TRACE_POINTS} points")

        next_time = self._time + delta * self._speed
        if not isfinite(next_time):
            raise DomainValidationError("timeline time must remain finite")
        next_chain = build_epicycle_chain(self._selection, next_time)
        self._time = next_time
        self._chain = next_chain
        self._trace.append(self._chain.endpoint)
        return self._frame()

    def set_speed(self, speed: float) -> EpicycleFrame:
        self._speed = validate_timeline_speed(speed)
        return self._frame()

    def set_harmonic_count(self, harmonic_count: int) -> EpicycleFrame:
        selection = self._make_selection(harmonic_count)
        reconstruction = self._make_reconstruction(selection)
        chain = build_epicycle_chain(selection, self._time)
        self._selection = selection
        self._reconstruction = reconstruction
        self._chain = chain
        self._trace = [self._chain.endpoint]
        return self._frame()

    def set_visibility(self, **changes: bool) -> EpicycleFrame:
        allowed = set(RenderVisibility.__dataclass_fields__)
        if not changes or not set(changes).issubset(allowed):
            raise DomainValidationError("visibility changes contain an unknown layer")
        if any(not isinstance(value, bool) for value in changes.values()):
            raise DomainValidationError("visibility values must be booleans")
        self._visibility = replace(self._visibility, **changes)
        return self._frame()

    def _make_selection(self, harmonic_count: int) -> CoefficientSelection:
        if isinstance(harmonic_count, bool) or not isinstance(harmonic_count, int):
            raise DomainValidationError("harmonic_count must be an integer")
        if harmonic_count < 1 or harmonic_count > self.maximum_harmonics:
            raise DomainValidationError(
                f"harmonic_count must be between 1 and {self.maximum_harmonics}"
            )
        return select_first(self._spectrum, harmonic_count, self._ordering)

    def _make_reconstruction(
        self,
        selection: CoefficientSelection | None = None,
    ) -> Curve:
        return complex_samples_to_curve(
            reconstruct_samples(selection or self._selection),
            closed=self._original.closed,
        )

    def _frame(self) -> EpicycleFrame:
        return EpicycleFrame(
            chain=self._chain,
            trace=tuple(self._trace),
            visibility=self._visibility,
            selection=self._selection,
            original=self._original,
            reconstruction=self._reconstruction,
            timeline_state=self._state,
            speed=self._speed,
        )


def validate_timeline_speed(value: float) -> float:
    """Validate and normalize the shared interactive timeline speed contract."""
    normalized = _finite_real(value, field_name="speed")
    if normalized <= 0.0 or normalized > MAX_SPEED:
        raise DomainValidationError(f"speed must be greater than zero and at most {MAX_SPEED}")
    return normalized


def _validated_delta(value: float) -> float:
    normalized = _finite_real(value, field_name="delta_seconds")
    if normalized < 0.0:
        raise DomainValidationError("delta_seconds must be non-negative")
    return normalized


def _finite_real(value: float, *, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DomainValidationError(f"{field_name} must be a finite real number")
    try:
        normalized = float(value)
    except OverflowError as error:
        raise DomainValidationError(f"{field_name} must be finite") from error
    if not isfinite(normalized):
        raise DomainValidationError(f"{field_name} must be finite")
    return normalized
