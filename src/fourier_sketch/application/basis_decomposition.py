"""Explicit Fourier/Haar curve decomposition adapters and Haar animation state."""

from dataclasses import dataclass
from math import floor, isfinite

from fourier_sketch.domain import (
    BasisKind,
    Curve,
    DomainValidationError,
    HaarDecomposition,
    HaarSelection,
    HaarTerm,
)
from fourier_sketch.math import (
    MAX_HAAR_SAMPLES,
    complex_samples_to_curve,
    curve_to_complex_samples,
    fft_dft,
    haar_analyze,
    haar_synthesize,
    haar_term_contribution,
    resample_curve_by_arc_length,
    select_haar_terms,
)

from .diagnostic_epicycles import (
    EpicycleTimeline,
    TimelineState,
    validate_timeline_speed,
)

HAAR_ANALYSIS_SAMPLES = 128
MAX_HAAR_SOURCE_POINTS = 10_000
HAAR_TERMS_PER_SECOND = 4.0
HAAR_MIN_SPEED = 0.01
HAAR_MAX_SPEED = 1.0
DEFAULT_BASIS_HARMONICS = 15


@dataclass(frozen=True, slots=True)
class HaarFrame:
    """Immutable renderer input for scale/location reconstruction."""

    source: Curve
    analysis: Curve
    reconstruction: Curve
    active_contribution: Curve
    decomposition: HaarDecomposition
    selection: HaarSelection
    state: TimelineState
    speed: float

    def __post_init__(self) -> None:
        if not all(
            isinstance(value, Curve)
            for value in (self.source, self.analysis, self.reconstruction, self.active_contribution)
        ):
            raise DomainValidationError("Haar frame curves must be Curve values")
        if not isinstance(self.decomposition, HaarDecomposition):
            raise DomainValidationError("Haar frame decomposition must be a HaarDecomposition")
        if not isinstance(self.selection, HaarSelection):
            raise DomainValidationError("Haar frame selection must be a HaarSelection")
        if self.selection.sample_count != self.decomposition.sample_count:
            raise DomainValidationError("Haar frame selection/decomposition grids must match")
        if self.analysis.sample_count != self.decomposition.sample_count:
            raise DomainValidationError("Haar analysis curve must match decomposition grid")
        if self.reconstruction.sample_count != self.analysis.sample_count:
            raise DomainValidationError("Haar reconstruction must match analysis grid")
        if self.active_contribution.sample_count != self.analysis.sample_count:
            raise DomainValidationError("Haar contribution must match analysis grid")
        if self.source.closed != self.analysis.closed:
            raise DomainValidationError("Haar source and analysis topology must match")
        if not isinstance(self.state, TimelineState):
            raise DomainValidationError("Haar frame state must be a TimelineState")
        object.__setattr__(self, "speed", _validated_haar_speed(self.speed))

    @property
    def term_count(self) -> int:
        return self.selection.term_count

    @property
    def total_terms(self) -> int:
        return self.decomposition.sample_count

    @property
    def basis(self) -> BasisKind:
        return BasisKind.HAAR_WAVELET

    @property
    def source_curve(self) -> Curve:
        return self.source

    @property
    def analysis_curve(self) -> Curve:
        """Named alias used by presentation adapters."""
        return self.analysis

    @property
    def timeline_state(self) -> TimelineState:
        return self.state

    @property
    def active_term(self) -> HaarTerm:
        return self.selection.terms[-1]

    @property
    def active_term_contribution(self) -> Curve:
        return self.active_contribution


class HaarTimeline:
    """Bounded deterministic animation of a Haar term prefix."""

    def __init__(
        self,
        source: Curve,
        analysis: Curve,
        decomposition: HaarDecomposition,
        *,
        term_count: int = 1,
        speed: float = 1.0,
    ) -> None:
        _validate_hair_inputs(source, analysis, decomposition)
        self._source = source
        self._analysis = analysis
        self._decomposition = decomposition
        self._term_count = _validated_term_count(term_count, decomposition.sample_count)
        self._speed = _validated_haar_speed(speed)
        self._state = TimelineState.PAUSED
        self._elapsed = 0.0

    @property
    def state(self) -> TimelineState:
        return self._state

    @property
    def speed(self) -> float:
        return self._speed

    @property
    def term_count(self) -> int:
        return self._term_count

    @property
    def maximum_terms(self) -> int:
        return self._decomposition.sample_count

    @property
    def source(self) -> Curve:
        return self._source

    @property
    def source_curve(self) -> Curve:
        return self._source

    @property
    def analysis(self) -> Curve:
        return self._analysis

    @property
    def analysis_curve(self) -> Curve:
        return self._analysis

    @property
    def decomposition(self) -> HaarDecomposition:
        return self._decomposition

    @property
    def basis(self) -> BasisKind:
        return BasisKind.HAAR_WAVELET

    def snapshot(self) -> HaarFrame:
        selection = select_haar_terms(self._decomposition, self._term_count)
        reconstruction = complex_samples_to_curve(
            haar_synthesize(selection),
            closed=self._analysis.closed,
        )
        contribution = complex_samples_to_curve(
            haar_term_contribution(selection.terms[-1], self._analysis.sample_count),
            closed=self._analysis.closed,
        )
        return HaarFrame(
            source=self._source,
            analysis=self._analysis,
            reconstruction=reconstruction,
            active_contribution=contribution,
            decomposition=self._decomposition,
            selection=selection,
            state=self._state,
            speed=self._speed,
        )

    def play(self) -> HaarFrame:
        if self._term_count < self.maximum_terms:
            self._state = TimelineState.RUNNING
        return self.snapshot()

    def pause(self) -> HaarFrame:
        self._state = TimelineState.PAUSED
        return self.snapshot()

    def restart(self) -> HaarFrame:
        self._state = TimelineState.PAUSED
        self._term_count = 1
        self._elapsed = 0.0
        return self.snapshot()

    def advance(self, delta_seconds: float) -> HaarFrame:
        delta = _validated_delta(delta_seconds)
        if self._state is TimelineState.RUNNING and delta:
            elapsed = self._elapsed + delta * self._speed * HAAR_TERMS_PER_SECOND
            if not isfinite(elapsed):
                raise DomainValidationError("Haar activation accumulator must remain finite")
            transitions = min(
                self.maximum_terms - self._term_count,
                floor(elapsed),
            )
            if transitions:
                self._term_count += transitions
                elapsed -= transitions
                if self._term_count == self.maximum_terms:
                    self._state = TimelineState.PAUSED
                    elapsed = 0.0
            self._elapsed = elapsed
        return self.snapshot()

    def set_term_count(self, term_count: int) -> HaarFrame:
        self._term_count = _validated_term_count(term_count, self.maximum_terms)
        self._elapsed = 0.0
        if self._term_count == self.maximum_terms:
            self._state = TimelineState.PAUSED
        return self.snapshot()

    def set_speed(self, speed: float) -> HaarFrame:
        self._speed = _validated_haar_speed(speed)
        return self.snapshot()


def build_basis_timeline(
    curve: Curve,
    *,
    basis: BasisKind = BasisKind.FOURIER_EPICYCLE,
    harmonic_count: int | None = None,
    term_count: int | None = None,
    speed: float = 1.0,
) -> EpicycleTimeline | HaarTimeline:
    """Build the selected basis without silently switching on failure."""
    if not isinstance(curve, Curve):
        raise DomainValidationError("curve must be a Curve")
    if basis is BasisKind.FOURIER_EPICYCLE:
        count = min(DEFAULT_BASIS_HARMONICS, curve.sample_count)
        if harmonic_count is not None:
            count = _validated_term_count(harmonic_count, curve.sample_count)
        return EpicycleTimeline(
            fft_dft(curve_to_complex_samples(curve)),
            curve,
            harmonic_count=count,
            speed=speed,
        )
    if basis is BasisKind.HAAR_WAVELET:
        if harmonic_count is not None:
            raise DomainValidationError("harmonic_count is only valid for Fourier basis")
        analysis = _make_analysis_curve(curve)
        decomposition = haar_analyze(
            curve_to_complex_samples(analysis),
            provenance=(
                ("basis", BasisKind.HAAR_WAVELET.value),
                ("source_sample_count", str(curve.sample_count)),
                ("analysis_sample_count", str(analysis.sample_count)),
            ),
        )
        count = 1 if term_count is None else term_count
        return HaarTimeline(
            curve,
            analysis,
            decomposition,
            term_count=count,
            speed=speed,
        )
    raise DomainValidationError("unsupported basis; choose Fourier epicycles or Haar wavelet")


def build_basis_decomposition(
    curve: Curve,
    *,
    basis: BasisKind = BasisKind.FOURIER_EPICYCLE,
    harmonic_count: int | None = None,
    term_count: int | None = None,
    speed: float = 1.0,
) -> EpicycleTimeline | HaarTimeline:
    """Compatibility name for the explicit basis timeline adapter."""
    return build_basis_timeline(
        curve,
        basis=basis,
        harmonic_count=harmonic_count,
        term_count=term_count,
        speed=speed,
    )


def build_haar_timeline(
    curve: Curve,
    *,
    term_count: int = 1,
    speed: float = 1.0,
) -> HaarTimeline:
    """Build the explicit Haar branch."""
    result = build_basis_timeline(
        curve,
        basis=BasisKind.HAAR_WAVELET,
        term_count=term_count,
        speed=speed,
    )
    if not isinstance(result, HaarTimeline):
        raise DomainValidationError("Haar adapter did not produce a HaarTimeline")
    return result


def _make_analysis_curve(curve: Curve) -> Curve:
    if curve.sample_count > MAX_HAAR_SOURCE_POINTS:
        raise DomainValidationError(
            f"Haar source must not exceed {MAX_HAAR_SOURCE_POINTS} points"
        )
    if curve.sample_count == 1:
        return curve
    return resample_curve_by_arc_length(curve, HAAR_ANALYSIS_SAMPLES)


def _validate_hair_inputs(
    source: Curve,
    analysis: Curve,
    decomposition: HaarDecomposition,
) -> None:
    if not isinstance(source, Curve) or not isinstance(analysis, Curve):
        raise DomainValidationError("Haar timeline curves must be Curve values")
    if not isinstance(decomposition, HaarDecomposition):
        raise DomainValidationError("Haar timeline decomposition must be a HaarDecomposition")
    if analysis.sample_count != decomposition.sample_count:
        raise DomainValidationError("analysis curve and decomposition sample_count must match")
    if analysis.sample_count > MAX_HAAR_SAMPLES:
        raise DomainValidationError("analysis curve exceeds Haar budget")


def _validated_term_count(value: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise DomainValidationError("Haar term_count must be an integer")
    if value < 1 or value > maximum:
        raise DomainValidationError(f"Haar term_count must be between 1 and {maximum}")
    return value


def _validated_delta(value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DomainValidationError("delta_seconds must be a finite real number")
    normalized = float(value)
    if not isfinite(normalized) or normalized < 0.0:
        raise DomainValidationError("delta_seconds must be finite and non-negative")
    return normalized


def _validated_haar_speed(value: float) -> float:
    normalized = validate_timeline_speed(value)
    if normalized < HAAR_MIN_SPEED or normalized > HAAR_MAX_SPEED:
        raise DomainValidationError(
            f"Haar speed must be between {HAAR_MIN_SPEED} and {HAAR_MAX_SPEED}"
        )
    return normalized
