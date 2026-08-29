"""Application use cases for Fourier Sketch."""

from fourier_sketch.math import ResamplingMethod

from .diagnostic_epicycles import (
    EpicycleFrame,
    EpicycleTimeline,
    RenderVisibility,
    TimelineState,
    validate_timeline_speed,
)
from .discontinuous_fourier import (
    DiscontinuitySpectrumComparison,
    DiscontinuousFourierResult,
    DiscontinuousMode,
    ForcedRouteFourierComparison,
    analyze_discontinuity_vs_continuous,
    build_discontinuous_fourier,
    compare_discontinuous_with_forced_route,
)
from .dominant_contour import (
    DEFAULT_CONTOUR_HARMONICS,
    DEFAULT_CONTOUR_SAMPLES,
    ImageContourTimelineResult,
    ImageNoContourResult,
    build_dominant_contour_timeline,
)
from .edge_detection import detect_preprocessed_edges, export_edge_result
from .forced_route import (
    DEFAULT_ROUTE_HARMONICS,
    DEFAULT_ROUTE_SAMPLES,
    LocalForcedRouteResult,
    build_local_forced_route,
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
from .image_mvp import (
    ImageMvpConfig,
    ImageMvpController,
    ImageMvpResult,
    ImageMvpSnapshot,
    ImageMvpState,
)
from .image_preprocessing import (
    export_preprocessing_result,
    preprocess_local_image,
    select_preprocessing_raster,
)
from .local_paths import LocalPathError, validate_local_path
from .piecewise_skeleton import LocalPiecewiseResult, build_local_piecewise
from .skeleton_graph import (
    LocalSkeletonGraphResult,
    build_local_skeleton_graph,
    export_skeleton_graph_json,
)
from .skeletonization import (
    LocalSkeletonResult,
    SkeletonConfig,
    SkeletonController,
    SkeletonSnapshot,
    SkeletonState,
    build_local_skeleton,
    export_local_skeleton,
)

__all__ = [
    "DEFAULT_CONTOUR_HARMONICS",
    "DEFAULT_CONTOUR_SAMPLES",
    "DEFAULT_FREEHAND_HARMONICS",
    "DEFAULT_FREEHAND_SAMPLES",
    "DEFAULT_ROUTE_HARMONICS",
    "DEFAULT_ROUTE_SAMPLES",
    "MAX_CAPTURE_POINTS",
    "CaptureState",
    "DiscontinuitySpectrumComparison",
    "DiscontinuousFourierResult",
    "DiscontinuousMode",
    "EpicycleFrame",
    "EpicycleTimeline",
    "ForcedRouteFourierComparison",
    "FreehandCapture",
    "FreehandCaptureSnapshot",
    "FreehandCurveResult",
    "ImageContourTimelineResult",
    "ImageMvpConfig",
    "ImageMvpController",
    "ImageMvpResult",
    "ImageMvpSnapshot",
    "ImageMvpState",
    "ImageNoContourResult",
    "LocalForcedRouteResult",
    "LocalPathError",
    "LocalPiecewiseResult",
    "LocalSkeletonGraphResult",
    "LocalSkeletonResult",
    "RenderVisibility",
    "ResamplingMethod",
    "SkeletonConfig",
    "SkeletonController",
    "SkeletonSnapshot",
    "SkeletonState",
    "TimelineState",
    "analyze_discontinuity_vs_continuous",
    "build_discontinuous_fourier",
    "build_dominant_contour_timeline",
    "build_freehand_timeline",
    "build_local_forced_route",
    "build_local_piecewise",
    "build_local_skeleton",
    "build_local_skeleton_graph",
    "compare_discontinuous_with_forced_route",
    "detect_preprocessed_edges",
    "export_edge_result",
    "export_local_skeleton",
    "export_preprocessing_result",
    "export_skeleton_graph_json",
    "preprocess_local_image",
    "select_preprocessing_raster",
    "validate_local_path",
    "validate_timeline_speed",
]
