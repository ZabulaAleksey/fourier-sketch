"""Application use cases for Fourier Sketch."""

from fourier_sketch.math import ResamplingMethod

from .diagnostic_epicycles import (
    EpicycleFrame,
    EpicycleTimeline,
    RenderVisibility,
    TimelineState,
)
from .dominant_contour import (
    DEFAULT_CONTOUR_HARMONICS,
    DEFAULT_CONTOUR_SAMPLES,
    ImageContourTimelineResult,
    ImageNoContourResult,
    build_dominant_contour_timeline,
)
from .edge_detection import detect_preprocessed_edges, export_edge_result
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
    "DEFAULT_CONTOUR_HARMONICS",
    "DEFAULT_CONTOUR_SAMPLES",
    "DEFAULT_FREEHAND_HARMONICS",
    "DEFAULT_FREEHAND_SAMPLES",
    "MAX_CAPTURE_POINTS",
    "CaptureState",
    "EpicycleFrame",
    "EpicycleTimeline",
    "FreehandCapture",
    "FreehandCaptureSnapshot",
    "FreehandCurveResult",
    "ImageContourTimelineResult",
    "ImageNoContourResult",
    "RenderVisibility",
    "ResamplingMethod",
    "TimelineState",
    "build_dominant_contour_timeline",
    "build_freehand_timeline",
    "detect_preprocessed_edges",
    "export_edge_result",
    "export_preprocessing_result",
    "preprocess_local_image",
    "select_preprocessing_raster",
]
