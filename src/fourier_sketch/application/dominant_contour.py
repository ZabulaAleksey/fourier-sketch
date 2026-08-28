"""FS-012 composition from accepted edge intermediates to the proven timeline."""

from dataclasses import dataclass

from fourier_sketch.application.diagnostic_epicycles import (
    EpicycleTimeline,
    validate_timeline_speed,
)
from fourier_sketch.application.edge_detection import detect_preprocessed_edges
from fourier_sketch.application.freehand import build_freehand_timeline
from fourier_sketch.domain import Curve, DomainValidationError
from fourier_sketch.imaging import (
    CannyParameters,
    EdgeAlgorithm,
    EdgeDetectionResult,
    ImagePreprocessingResult,
    ThresholdBoundaryParameters,
    extract_external_contours,
)
from fourier_sketch.math import resample_curve_by_arc_length
from fourier_sketch.routing import (
    DominantContourSelection,
    NoContourResult,
    NormalizedContourCurve,
    normalize_selected_contour,
    select_dominant_contour,
)

DEFAULT_CONTOUR_SAMPLES = 256
DEFAULT_CONTOUR_HARMONICS = 25

_DEFAULT_BOUNDARY_PARAMETERS = ThresholdBoundaryParameters()
_DEFAULT_CANNY_PARAMETERS = CannyParameters()


@dataclass(frozen=True, slots=True)
class ImageNoContourResult:
    """Valid empty application result with all upstream provenance retained."""

    preprocessing: ImagePreprocessingResult
    edges: EdgeDetectionResult
    no_contour: NoContourResult

    def __post_init__(self) -> None:
        if not isinstance(self.preprocessing, ImagePreprocessingResult):
            raise DomainValidationError("image contour result requires preprocessing provenance")
        if not isinstance(self.edges, EdgeDetectionResult) or not isinstance(
            self.no_contour, NoContourResult
        ):
            raise DomainValidationError("image no-contour result requires typed values")
        dimensions = (self.preprocessing.binary.width, self.preprocessing.binary.height)
        if self.edges.source_dimensions != dimensions:
            raise DomainValidationError("edge result dimensions must match preprocessing")
        if self.no_contour.extraction.source != self.edges:
            raise DomainValidationError("no-contour extraction must match the edge result")


@dataclass(frozen=True, slots=True)
class ImageContourTimelineResult:
    """Successful single-contour curve, sampling and actual timeline composition."""

    preprocessing: ImagePreprocessingResult
    edges: EdgeDetectionResult
    selection: DominantContourSelection
    normalized: NormalizedContourCurve
    sampled_curve: Curve
    timeline: EpicycleTimeline

    def __post_init__(self) -> None:
        if not isinstance(self.preprocessing, ImagePreprocessingResult):
            raise DomainValidationError("image contour result requires preprocessing provenance")
        if not isinstance(self.edges, EdgeDetectionResult):
            raise DomainValidationError("image contour result requires an edge result")
        dimensions = (self.preprocessing.binary.width, self.preprocessing.binary.height)
        if self.edges.source_dimensions != dimensions:
            raise DomainValidationError("edge result dimensions must match preprocessing")
        if not isinstance(self.selection, DominantContourSelection) or not isinstance(
            self.normalized, NormalizedContourCurve
        ):
            raise DomainValidationError("image contour result requires typed contour values")
        if self.selection.extraction.source != self.edges:
            raise DomainValidationError("contour extraction must match the edge result")
        if self.normalized.selection != self.selection:
            raise DomainValidationError("normalized contour must match the selected candidate")
        if not isinstance(self.sampled_curve, Curve) or not self.sampled_curve.closed:
            raise DomainValidationError("sampled image contour must be a closed Curve")
        if not isinstance(self.timeline, EpicycleTimeline):
            raise DomainValidationError("image contour result requires an epicycle timeline")
        if self.timeline.snapshot().original != self.sampled_curve:
            raise DomainValidationError("timeline must use the sampled contour curve")


def build_dominant_contour_timeline(
    preprocessing: ImagePreprocessingResult,
    algorithm: EdgeAlgorithm,
    *,
    sample_count: int = DEFAULT_CONTOUR_SAMPLES,
    harmonic_count: int = DEFAULT_CONTOUR_HARMONICS,
    speed: float = 1.0,
    boundary_parameters: ThresholdBoundaryParameters = _DEFAULT_BOUNDARY_PARAMETERS,
    canny_parameters: CannyParameters = _DEFAULT_CANNY_PARAMETERS,
) -> ImageContourTimelineResult | ImageNoContourResult:
    """Compose preprocessing through one dominant contour into the accepted timeline."""
    if not isinstance(preprocessing, ImagePreprocessingResult):
        raise DomainValidationError("dominant contour pipeline requires preprocessing result")
    if not isinstance(algorithm, EdgeAlgorithm):
        raise DomainValidationError("dominant contour pipeline requires an explicit edge algorithm")
    if type(sample_count) is not int or not 3 <= sample_count <= 4096:
        raise DomainValidationError("contour sample_count must be between 3 and 4096")
    if type(harmonic_count) is not int or not 1 <= harmonic_count <= sample_count:
        raise DomainValidationError("contour harmonic_count must be between 1 and sample_count")
    normalized_speed = validate_timeline_speed(speed)
    edges = detect_preprocessed_edges(
        preprocessing,
        algorithm,
        boundary_parameters=boundary_parameters,
        canny_parameters=canny_parameters,
    )
    extraction = extract_external_contours(edges)
    selection = select_dominant_contour(extraction)
    if isinstance(selection, NoContourResult):
        return ImageNoContourResult(
            preprocessing=preprocessing,
            edges=edges,
            no_contour=selection,
        )
    normalized = normalize_selected_contour(selection)
    sampled_curve = resample_curve_by_arc_length(normalized.curve, sample_count)
    timeline = build_freehand_timeline(
        sampled_curve,
        harmonic_count=harmonic_count,
        speed=normalized_speed,
    )
    return ImageContourTimelineResult(
        preprocessing=preprocessing,
        edges=edges,
        selection=selection,
        normalized=normalized,
        sampled_curve=sampled_curve,
        timeline=timeline,
    )
