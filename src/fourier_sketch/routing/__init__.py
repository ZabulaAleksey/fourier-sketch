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

__all__ = [
    "COORDINATE_TRANSFORM_ID",
    "DOMINANT_SELECTION_POLICY",
    "ORIENTATION_POLICY",
    "START_POINT_POLICY",
    "DominantContourSelection",
    "NoContourReason",
    "NoContourResult",
    "NormalizedContourCurve",
    "NormalizedContourProvenance",
    "canonical_pixel_signature",
    "normalize_selected_contour",
    "select_dominant_contour",
]
