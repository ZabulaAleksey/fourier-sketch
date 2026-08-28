"""Public domain model for Fourier Sketch."""

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
from .piecewise_curve import PiecewiseCurve
from .point import Point2D
from .selection import CoefficientSelection, NormalizedErrorStatus, ReconstructionMetrics

__all__ = [
    "CoefficientSelection",
    "Curve",
    "DomainValidationError",
    "EpicycleChainState",
    "EpicycleVector",
    "FourierCoefficient",
    "FourierNormalization",
    "FourierSpectrum",
    "FrequencyConvention",
    "NormalizedErrorStatus",
    "PiecewiseCurve",
    "Point2D",
    "ReconstructionMetrics",
    "SpectrumOrdering",
]
