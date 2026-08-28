"""Application use cases for Fourier Sketch."""

from fourier_sketch.math import ResamplingMethod

from .diagnostic_epicycles import (
    EpicycleFrame,
    EpicycleTimeline,
    RenderVisibility,
    TimelineState,
)
from .freehand import (
    DEFAULT_FREEHAND_HARMONICS,
    DEFAULT_FREEHAND_SAMPLES,
    MAX_CAPTURE_POINTS,
    CaptureState,
    FreehandCapture,
    FreehandCaptureSnapshot,
    FreehandCurveResult,
    build_freehand_timeline,
)
from .image_preprocessing import (
    export_preprocessing_result,
    preprocess_local_image,
    select_preprocessing_raster,
)

__all__ = [
    "DEFAULT_FREEHAND_HARMONICS",
    "DEFAULT_FREEHAND_SAMPLES",
    "MAX_CAPTURE_POINTS",
    "CaptureState",
    "EpicycleFrame",
    "EpicycleTimeline",
    "FreehandCapture",
    "FreehandCaptureSnapshot",
    "FreehandCurveResult",
    "RenderVisibility",
    "ResamplingMethod",
    "TimelineState",
    "build_freehand_timeline",
    "export_preprocessing_result",
    "preprocess_local_image",
    "select_preprocessing_raster",
]
