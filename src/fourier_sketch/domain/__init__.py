"""Public domain model for Fourier Sketch."""

from .basis import (
    BasisKind,
    HaarDecomposition,
    HaarNormalization,
    HaarOrdering,
    HaarSelection,
    HaarTerm,
    HaarTermKind,
)
from .curve import Curve
from .epicycle import EpicycleChainState, EpicycleVector
from .errors import DomainValidationError
from .fourier import (
    FourierCoefficient,
    FourierNormalization,
    FourierSpectrum,
    FrequencyConvention,
    SpectrumOrdering,
)
from .harmonic_playground import (
    PLAYGROUND_MAX_AMPLITUDE,
    PLAYGROUND_MAX_FREQUENCY,
    PLAYGROUND_MIN_FREQUENCY,
    PLAYGROUND_SAMPLE_COUNT,
    ManualHarmonic,
)
from .indexed_basis import (
    IndexedDecomposition,
    IndexedNormalization,
    IndexedOrdering,
    IndexedSelection,
    IndexedTerm,
)
from .piecewise_curve import PiecewiseCurve
from .point import Point2D
from .selection import CoefficientSelection, NormalizedErrorStatus, ReconstructionMetrics

__all__ = [
    "PLAYGROUND_MAX_AMPLITUDE",
    "PLAYGROUND_MAX_FREQUENCY",
    "PLAYGROUND_MIN_FREQUENCY",
    "PLAYGROUND_SAMPLE_COUNT",
    "BasisKind",
    "CoefficientSelection",
    "Curve",
    "DomainValidationError",
    "EpicycleChainState",
    "EpicycleVector",
    "FourierCoefficient",
    "FourierNormalization",
    "FourierSpectrum",
    "FrequencyConvention",
    "HaarDecomposition",
    "HaarNormalization",
    "HaarOrdering",
    "HaarSelection",
    "HaarTerm",
    "HaarTermKind",
    "IndexedDecomposition",
    "IndexedNormalization",
    "IndexedOrdering",
    "IndexedSelection",
    "IndexedTerm",
    "ManualHarmonic",
    "NormalizedErrorStatus",
    "PiecewiseCurve",
    "Point2D",
    "ReconstructionMetrics",
    "SpectrumOrdering",
]
