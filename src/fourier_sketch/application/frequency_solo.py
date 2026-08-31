"""Bounded one-frequency analysis projection over an immutable baseline frame."""

from fourier_sketch.domain import (
    CoefficientSelection,
    Curve,
    DomainValidationError,
    EpicycleChainState,
    FourierCoefficient,
    Point2D,
    SpectrumOrdering,
)
from fourier_sketch.math import (
    build_epicycle_chain,
    complex_samples_to_curve,
    reconstruct_samples,
)

from .diagnostic_epicycles import MAX_TRACE_POINTS, EpicycleFrame


class FrequencySoloSession:
    """Project baseline animation frames into one actual signed-frequency active set."""

    def __init__(self) -> None:
        self._frequency: int | None = None
        self._coefficient: FourierCoefficient | None = None
        self._original: Curve | None = None
        self._selection: CoefficientSelection | None = None
        self._reconstruction: Curve | None = None
        self._source: object | None = None
        self._trace: tuple[Point2D, ...] = ()
        self._last_time: float | None = None

    @property
    def active(self) -> bool:
        return self._frequency is not None

    @property
    def frequency(self) -> int | None:
        return self._frequency

    def enter(
        self,
        frame: EpicycleFrame,
        frequency: int,
        *,
        source: object,
    ) -> EpicycleFrame:
        """Start a transactional Solo session without mutating the baseline frame."""

        self._validate_frame(frame)
        self._validate_source(source)
        if self.active:
            raise DomainValidationError("frequency Solo is already active")
        coefficient = self._find_coefficient(frame, frequency)
        selection = CoefficientSelection(
            (coefficient,),
            frame.selection.sample_count,
            SpectrumOrdering.EXPLICIT,
        )
        chain, reconstruction = self._build_components(frame, selection)
        trace = (chain.endpoint,)
        projected = self._build_frame(frame, selection, chain, reconstruction, trace)
        self._frequency = frequency
        self._coefficient = coefficient
        self._original = frame.original
        self._selection = selection
        self._reconstruction = reconstruction
        self._source = source
        self._trace = trace
        self._last_time = frame.chain.time
        return projected

    def project(self, frame: EpicycleFrame, *, source: object) -> EpicycleFrame:
        """Project a new baseline frame while keeping a mode-local endpoint ledger."""

        self._validate_frame(frame)
        frequency = self._frequency
        if frequency is None:
            return frame
        if source is not self._source or frame.original is not self._original:
            self.clear()
            return frame
        try:
            coefficient = self._find_coefficient(frame, frequency)
        except DomainValidationError:
            self.clear()
            return frame
        if coefficient != self._coefficient:
            self.clear()
            return frame

        selection = self._selection
        reconstruction = self._reconstruction
        if selection is None or reconstruction is None:
            self.clear()
            return frame
        time = frame.chain.time
        chain = build_epicycle_chain(
            selection,
            time,
            origin=frame.chain.origin,
        )
        reset_trace = self._last_time is None or time < self._last_time
        trace = () if reset_trace else self._trace
        if not trace or time != self._last_time:
            if len(trace) >= MAX_TRACE_POINTS:
                raise DomainValidationError(
                    f"Solo trace must not exceed {MAX_TRACE_POINTS} points"
                )
            trace = (*trace, chain.endpoint)
        candidate = self._build_frame(
            frame,
            selection,
            chain,
            reconstruction,
            trace,
        )
        self._trace = trace
        self._last_time = time
        return candidate

    def exit(self, frame: EpicycleFrame, *, source: object) -> EpicycleFrame:
        """End Solo and reveal the exact supplied baseline frame."""

        self._validate_frame(frame)
        if not self.active:
            raise DomainValidationError("frequency Solo is not active")
        if source is not self._source:
            raise DomainValidationError("frequency Solo source does not match")
        self.clear()
        return frame

    def clear(self) -> None:
        """Forget analysis-only state; used when a new timeline replaces the baseline."""

        self._frequency = None
        self._coefficient = None
        self._original = None
        self._selection = None
        self._reconstruction = None
        self._source = None
        self._trace = ()
        self._last_time = None

    @staticmethod
    def _validate_frame(frame: EpicycleFrame) -> None:
        if not isinstance(frame, EpicycleFrame):
            raise DomainValidationError("frequency Solo requires an EpicycleFrame")

    @staticmethod
    def _validate_source(source: object) -> None:
        if source is None:
            raise DomainValidationError("frequency Solo requires a source owner")

    @staticmethod
    def _find_coefficient(
        frame: EpicycleFrame,
        frequency: int,
    ) -> FourierCoefficient:
        if isinstance(frequency, bool) or not isinstance(frequency, int):
            raise DomainValidationError("frequency must be an integer in the baseline selection")
        for coefficient in frame.selection.coefficients:
            if coefficient.frequency == frequency:
                return coefficient
        raise DomainValidationError("frequency is not available in the baseline selection")

    @staticmethod
    def _build_components(
        frame: EpicycleFrame,
        selection: CoefficientSelection,
    ) -> tuple[EpicycleChainState, Curve]:
        chain = build_epicycle_chain(
            selection,
            frame.chain.time,
            origin=frame.chain.origin,
        )
        origin = complex(frame.chain.origin.x, frame.chain.origin.y)
        reconstruction = complex_samples_to_curve(
            tuple(sample + origin for sample in reconstruct_samples(selection)),
            closed=frame.original.closed,
        )
        return chain, reconstruction

    @staticmethod
    def _build_frame(
        frame: EpicycleFrame,
        selection: CoefficientSelection,
        chain: EpicycleChainState,
        reconstruction: Curve,
        trace: tuple[Point2D, ...],
    ) -> EpicycleFrame:
        return EpicycleFrame(
            chain=chain,
            trace=trace,
            visibility=frame.visibility,
            selection=selection,
            original=frame.original,
            reconstruction=reconstruction,
            timeline_state=frame.timeline_state,
            speed=frame.speed,
        )
