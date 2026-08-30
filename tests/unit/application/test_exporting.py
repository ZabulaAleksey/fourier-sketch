"""Versioned data and bounded animation-plan contracts for FS-022."""

import csv
import json
from io import StringIO
from pathlib import Path

import pytest

from fourier_sketch.application import (
    AnimationExportPlan,
    EpicycleFrame,
    ExportCancelled,
    ExportFormat,
    build_freehand_timeline,
    export_coefficient_data,
    export_curve_data,
    iter_animation_frames,
    mp4_capability,
)
from fourier_sketch.domain import Curve, DomainValidationError, Point2D
from fourier_sketch.math import build_epicycle_chain


def _frame() -> EpicycleFrame:
    curve = Curve(
        (
            Point2D(1.0, 0.0),
            Point2D(0.0, 1.0),
            Point2D(-1.0, 0.0),
            Point2D(0.0, -1.0),
        ),
        closed=True,
    )
    return build_freehand_timeline(curve).snapshot()


def test_curve_and_coefficient_exports_are_versioned_and_order_preserving(
    tmp_path: Path,
) -> None:
    frame = _frame()
    curve_json = tmp_path / "curve.json"
    curve_csv = tmp_path / "curve.csv"
    coefficient_json = tmp_path / "coefficients.json"
    coefficient_csv = tmp_path / "coefficients.csv"

    export_curve_data(frame.original, curve_json, format=ExportFormat.CURVE_JSON)
    export_curve_data(frame.original, curve_csv, format=ExportFormat.CURVE_CSV)
    export_coefficient_data(
        frame.selection,
        coefficient_json,
        format=ExportFormat.COEFFICIENTS_JSON,
    )
    export_coefficient_data(
        frame.selection,
        coefficient_csv,
        format=ExportFormat.COEFFICIENTS_CSV,
    )

    curve_payload = json.loads(curve_json.read_text(encoding="utf-8"))
    assert curve_payload["schema"] == "fourier-sketch.curve"
    assert curve_payload["version"] == 1
    assert [(point["x"], point["y"]) for point in curve_payload["points"]] == [
        (point.x, point.y) for point in frame.original.points
    ]
    curve_rows = list(csv.DictReader(StringIO(curve_csv.read_text(encoding="utf-8"))))
    assert [int(row["index"]) for row in curve_rows] == list(range(frame.original.sample_count))

    coefficient_payload = json.loads(coefficient_json.read_text(encoding="utf-8"))
    assert coefficient_payload["schema"] == "fourier-sketch.coefficient-selection"
    assert coefficient_payload["ordering"] == frame.selection.ordering.value
    assert [item["frequency"] for item in coefficient_payload["coefficients"]] == list(
        frame.selection.frequencies
    )
    coefficient_rows = list(csv.DictReader(StringIO(coefficient_csv.read_text(encoding="utf-8"))))
    assert [int(row["frequency"]) for row in coefficient_rows] == list(frame.selection.frequencies)


def test_data_export_preserves_existing_destination_and_rejects_wrong_suffix(
    tmp_path: Path,
) -> None:
    frame = _frame()
    output = tmp_path / "curve.json"
    output.write_text("keep", encoding="utf-8")

    with pytest.raises(FileExistsError):
        export_curve_data(frame.original, output, format=ExportFormat.CURVE_JSON)
    assert output.read_text(encoding="utf-8") == "keep"
    with pytest.raises(DomainValidationError, match="extension"):
        export_curve_data(
            frame.original,
            tmp_path / "curve.txt",
            format=ExportFormat.CURVE_JSON,
        )


def test_data_export_cancelled_before_publication_leaves_no_artifact(tmp_path: Path) -> None:
    output = tmp_path / "curve.json"
    calls = 0

    def cancelled() -> bool:
        nonlocal calls
        calls += 1
        return calls > 1

    with pytest.raises(ExportCancelled):
        export_curve_data(
            _frame().original,
            output,
            format=ExportFormat.CURVE_JSON,
            cancelled=cancelled,
        )

    assert not output.exists()
    assert not tuple(tmp_path.glob(".curve.*.tmp"))


def test_no_overwrite_link_failure_leaves_no_partial_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "curve.json"

    def fail_link(*_args: object, **_kwargs: object) -> None:
        raise OSError("hard links unavailable")

    monkeypatch.setattr("fourier_sketch.application.exporting.os.link", fail_link)

    with pytest.raises(OSError, match="hard links unavailable"):
        export_curve_data(_frame().original, output, format=ExportFormat.CURVE_JSON)

    assert not output.exists()
    assert not tuple(tmp_path.glob(".curve.*.tmp"))


def test_animation_plan_uses_actual_chain_endpoints_and_cancels_cooperatively() -> None:
    frame = _frame()
    plan = AnimationExportPlan(frame, frame_count=4, frame_duration_ms=50)
    frames = tuple(iter_animation_frames(plan))

    assert all(item.trace[-1] == item.chain.endpoint for item in frames)
    assert tuple(item.chain.endpoint for item in frames) == tuple(
        build_epicycle_chain(
            frame.selection,
            frame.chain.time + index * 0.05 * frame.speed,
            origin=frame.chain.origin,
        ).endpoint
        for index in range(4)
    )
    assert frames[-1].trace == tuple(item.chain.endpoint for item in frames)

    calls = 0

    def cancelled() -> bool:
        nonlocal calls
        calls += 1
        return calls > 2

    with pytest.raises(ExportCancelled):
        tuple(iter_animation_frames(plan, cancelled=cancelled))


@pytest.mark.parametrize("frame_count", [1, 121])
def test_animation_plan_rejects_out_of_budget_frames(frame_count: int) -> None:
    with pytest.raises(DomainValidationError, match="frame_count"):
        AnimationExportPlan(_frame(), frame_count=frame_count)


def test_mp4_is_explicitly_unavailable() -> None:
    capability = mp4_capability()
    assert capability.available is False
    assert "no reviewed MP4 backend" in capability.reason
