"""Project-owned contour selection and routing policies."""

from .dominant_contour import (
    COORDINATE_TRANSFORM_ID,
    DOMINANT_SELECTION_POLICY,
    ORIENTATION_POLICY,
    START_POINT_POLICY,
    DominantContourSelection,
    NoContourReason,
    NoContourResult,
    NormalizedContourCurve,
    NormalizedContourProvenance,
    canonical_pixel_signature,
    normalize_selected_contour,
    select_dominant_contour,
)
from .forced_route import (
    DEFAULT_MAX_OPTIMIZATION_EXPANSIONS,
    ForcedRouteAlgorithm,
    ForcedRouteMetrics,
    ForcedRouteResult,
    ForcedRouteStatus,
    ForcedRouteStep,
    RouteStepKind,
    build_forced_route,
)
from .piecewise_components import (
    PiecewiseBuildStatus,
    PiecewiseComponentResult,
    PiecewiseSegment,
    PiecewiseSegmentProvenance,
    build_piecewise_components,
)
from .raster_coordinates import RasterCoordinateTransform

__all__ = [
    "COORDINATE_TRANSFORM_ID",
    "DEFAULT_MAX_OPTIMIZATION_EXPANSIONS",
    "DOMINANT_SELECTION_POLICY",
    "ORIENTATION_POLICY",
    "START_POINT_POLICY",
    "DominantContourSelection",
    "ForcedRouteAlgorithm",
    "ForcedRouteMetrics",
    "ForcedRouteResult",
    "ForcedRouteStatus",
    "ForcedRouteStep",
    "NoContourReason",
    "NoContourResult",
    "NormalizedContourCurve",
    "NormalizedContourProvenance",
    "PiecewiseBuildStatus",
    "PiecewiseComponentResult",
    "PiecewiseSegment",
    "PiecewiseSegmentProvenance",
    "RasterCoordinateTransform",
    "RouteStepKind",
    "build_forced_route",
    "build_piecewise_components",
    "canonical_pixel_signature",
    "normalize_selected_contour",
    "select_dominant_contour",
]
