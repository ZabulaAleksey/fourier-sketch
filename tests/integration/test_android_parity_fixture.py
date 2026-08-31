"""Ensure the versioned FS-031 corpus remains owned by the Python reference."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fourier_sketch.domain import Curve, Point2D, SpectrumOrdering
from fourier_sketch.math import (
    build_epicycle_chain,
    curve_to_complex_samples,
    reference_dft,
    select_first,
)

FIXTURE = Path(__file__).parents[2] / "fixtures" / "android" / "fourier-parity-v1.json"


def test_android_fixture_matches_python_reference() -> None:
    document = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert document["schema_version"] == 1
    assert document["normalization"] == "forward_1_over_n"
    assert document["frequency_convention"] == "signed_fft_storage"
    tolerance = float(document["tolerance"])

    for case in document["cases"]:
        curve = Curve(tuple(Point2D(*point) for point in case["points"]), closed=False)
        spectrum = reference_dft(curve_to_complex_samples(curve))
        assert len(case["coefficients"]) == spectrum.sample_count
        for expected, actual in zip(case["coefficients"], spectrum.coefficients, strict=True):
            assert expected[0] == actual.frequency
            assert expected[1] == pytest.approx(actual.real, abs=tolerance, rel=tolerance)
            assert expected[2] == pytest.approx(actual.imaginary, abs=tolerance, rel=tolerance)

        for check in case["endpoint_checks"]:
            selection = select_first(
                spectrum,
                check["harmonic_count"],
                SpectrumOrdering.AMPLITUDE_DESCENDING,
            )
            assert check["frequencies"] == [item.frequency for item in selection.coefficients]
            endpoint = build_epicycle_chain(selection, check["time"]).endpoint
            assert check["endpoint"][0] == pytest.approx(
                endpoint.x, abs=tolerance, rel=tolerance
            )
            assert check["endpoint"][1] == pytest.approx(
                endpoint.y, abs=tolerance, rel=tolerance
            )
