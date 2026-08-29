"""FS-016 graph-to-piecewise topology and provenance contracts."""

import pytest

from fourier_sketch.domain import Curve, DomainValidationError, PiecewiseCurve, Point2D
from fourier_sketch.imaging import PixelPoint, RasterImage, RasterStage, SkeletonAlgorithm
from fourier_sketch.imaging.skeleton_graph import build_skeleton_graph
from fourier_sketch.imaging.skeleton_model import SkeletonizationResult
from fourier_sketch.routing import (
    PiecewiseBuildStatus,
    PiecewiseComponentResult,
    PiecewiseSegment,
    PiecewiseSegmentProvenance,
    RasterCoordinateTransform,
    build_piecewise_components,
)

pytestmark = pytest.mark.unit


def _graph(width: int, height: int, points: set[tuple[int, int]]):  # type: ignore[no-untyped-def]
    pixels = bytearray(width * height)
    for column, row in points:
        pixels[row * width + column] = 255
    raster = RasterImage(width, height, bytes(pixels), RasterStage.BINARY)
    skeleton = SkeletonizationResult(
        raster,
        raster,
        SkeletonAlgorithm.LEE,
        "scikit-image/0.26.0",
        (width, height),
        len(points),
        len(points),
    )
    return build_skeleton_graph(skeleton)


def test_path_loop_and_isolated_components_become_independent_segments() -> None:
    path = {(column, 1) for column in range(4)}
    loop = (
        {(column, row) for column in range(7, 11) for row in (0, 3)}
        | {(column, row) for column in (7, 10) for row in range(1, 3)}
    )
    isolated = {(13, 4)}
    graph = _graph(15, 6, path | loop | isolated)

    result = build_piecewise_components(graph)

    assert result.status is PiecewiseBuildStatus.READY
    assert result.piecewise is not None
    assert result.piecewise.segment_count == 3
    assert [segment.provenance.topology for segment in result.segments] == [
        "loop",
        "path",
        "isolated",
    ]
    assert [segment.curve.closed for segment in result.segments] == [True, False, False]
    assert [segment.boundary_after for segment in result.segments] == [True, True, False]
    assert {
        (pixel.column, pixel.row)
        for segment in result.segments
        for pixel in segment.provenance.raster_pixels
    } == path | loop | isolated
    assert all(
        segment.provenance.coordinate_transform == "pixel-center-centered-aspect-v1"
        for segment in result.segments
    )


def test_branched_component_is_unsupported_without_partial_curve() -> None:
    cross = {(column, 2) for column in range(5)} | {(2, row) for row in range(5)}

    result = build_piecewise_components(_graph(5, 5, cross))

    assert result.status is PiecewiseBuildStatus.UNSUPPORTED
    assert result.reason == "branched_or_complex"
    assert result.piecewise is None
    assert result.segments == ()


def test_empty_and_cancelled_results_are_explicit() -> None:
    empty = build_piecewise_components(_graph(2, 2, set()))
    cancelled = build_piecewise_components(
        _graph(3, 1, {(0, 0), (1, 0), (2, 0)}),
        cancellation_check=lambda: True,
    )

    assert empty.status is PiecewiseBuildStatus.EMPTY
    assert cancelled.status is PiecewiseBuildStatus.CANCELLED
    assert empty.piecewise is cancelled.piecewise is None


def test_single_pixel_uses_safe_origin_transform() -> None:
    result = build_piecewise_components(_graph(1, 1, {(0, 0)}))

    assert result.piecewise is not None
    assert result.piecewise.segments[0].start.x == 0.0
    assert result.piecewise.segments[0].start.y == 0.0
    assert result.segments[0].provenance.scale == 1.0


def test_cancellation_is_checked_inside_long_component_conversion() -> None:
    graph = _graph(9000, 1, {(column, 0) for column in range(9000)})
    calls = 0

    def cancel_after_first_batch() -> bool:
        nonlocal calls
        calls += 1
        return calls >= 3

    result = build_piecewise_components(graph, cancellation_check=cancel_after_first_batch)

    assert result.status is PiecewiseBuildStatus.CANCELLED
    assert result.piecewise is None
    assert result.segments == ()
    assert calls == 3


@pytest.mark.parametrize("scale", (float("nan"), float("inf"), True, 0.0, 1, 10**1000))
def test_public_raster_transform_rejects_invalid_scale(scale: object) -> None:
    with pytest.raises(DomainValidationError):
        RasterCoordinateTransform((1, 1), scale)  # type: ignore[arg-type]


@pytest.mark.parametrize("dimensions", ((1,), (1, 2, 3), (True, 1), (0, 1)))
def test_public_raster_transform_rejects_invalid_dimensions(
    dimensions: tuple[int, ...],
) -> None:
    with pytest.raises(DomainValidationError):
        RasterCoordinateTransform.for_dimensions(dimensions)  # type: ignore[arg-type]


def test_public_piecewise_result_rejects_untyped_status_and_missing_reason() -> None:
    graph = _graph(2, 2, set())

    with pytest.raises(DomainValidationError, match="status"):
        PiecewiseComponentResult(graph, "ready")  # type: ignore[arg-type]
    with pytest.raises(DomainValidationError, match="stable reason"):
        PiecewiseComponentResult(graph, PiecewiseBuildStatus.EMPTY)


def test_public_piecewise_segment_rejects_untyped_or_malformed_provenance() -> None:
    curve = Curve((Point2D(0.0, 0.0),))

    with pytest.raises(DomainValidationError, match="typed curve and provenance"):
        PiecewiseSegment(curve, "bad")  # type: ignore[arg-type]
    with pytest.raises(DomainValidationError, match="topology"):
        PiecewiseSegmentProvenance(
            0,
            (0,),
            (),
            (PixelPoint(0, 0),),
            "branched",
            "pixel-center-centered-aspect-v1",
            1.0,
        )


def test_ready_result_rejects_forged_pixel_scale_and_curve_provenance() -> None:
    graph = _graph(2, 2, {(0, 0)})
    valid = build_piecewise_components(graph)
    segment = valid.segments[0]

    forged_pixel = PiecewiseSegmentProvenance(
        0,
        (0,),
        (),
        (PixelPoint(1, 0),),
        "isolated",
        "pixel-center-centered-aspect-v1",
        2.0,
    )
    forged_pixel_curve = Curve((Point2D(1.0, 1.0),))
    with pytest.raises(DomainValidationError, match="exactly cover"):
        PiecewiseComponentResult(
            graph,
            PiecewiseBuildStatus.READY,
            PiecewiseCurve((forged_pixel_curve,)),
            (PiecewiseSegment(forged_pixel_curve, forged_pixel),),
        )

    forged_scale = PiecewiseSegmentProvenance(
        0,
        (0,),
        (),
        (PixelPoint(0, 0),),
        "isolated",
        "pixel-center-centered-aspect-v1",
        1.0,
    )
    original_curve = Curve((segment.curve.points[0],))
    with pytest.raises(DomainValidationError, match="scale"):
        PiecewiseComponentResult(
            graph,
            PiecewiseBuildStatus.READY,
            PiecewiseCurve((original_curve,)),
            (PiecewiseSegment(original_curve, forged_scale),),
        )

    forged_curve = Curve((Point2D(0.0, 0.0),))
    with pytest.raises(DomainValidationError, match="coordinates"):
        PiecewiseComponentResult(
            graph,
            PiecewiseBuildStatus.READY,
            PiecewiseCurve((forged_curve,)),
            (PiecewiseSegment(forged_curve, segment.provenance),),
        )


def test_ready_result_rejects_reversed_graph_path_order() -> None:
    graph = _graph(4, 1, {(column, 0) for column in range(4)})
    valid = build_piecewise_components(graph)
    segment = valid.segments[0]
    reversed_pixels = tuple(reversed(segment.provenance.raster_pixels))
    transform = RasterCoordinateTransform.for_dimensions((4, 1))
    reversed_curve = Curve(transform.points(reversed_pixels))
    reversed_provenance = PiecewiseSegmentProvenance(
        segment.provenance.component_id,
        segment.provenance.node_ids,
        segment.provenance.edge_ids,
        reversed_pixels,
        segment.provenance.topology,
        segment.provenance.coordinate_transform,
        segment.provenance.scale,
    )

    with pytest.raises(DomainValidationError, match="canonical graph order"):
        PiecewiseComponentResult(
            graph,
            PiecewiseBuildStatus.READY,
            PiecewiseCurve((reversed_curve,)),
            (PiecewiseSegment(reversed_curve, reversed_provenance),),
        )
