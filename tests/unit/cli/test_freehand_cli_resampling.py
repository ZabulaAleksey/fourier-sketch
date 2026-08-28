"""Unit contract for the explicit FS-009 CLI method selector."""

from typing import Any

import pytest

from fourier_sketch.cli import freehand
from fourier_sketch.math import ResamplingMethod

pytestmark = pytest.mark.unit


def test_cli_passes_arc_length_enum_to_the_existing_interactive_entry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: dict[str, Any] = {}

    def record_call(*_args: object, **options: object) -> None:
        received.update(options)

    monkeypatch.setattr(freehand, "run_freehand_interactive", record_call)

    result = freehand.main(("--resampling", "arc_length", "--samples", "32"))

    assert result == 0
    assert received["resampling_method"] is ResamplingMethod.ARC_LENGTH
    assert received["sample_count"] == 32


def test_cli_rejects_unknown_method_through_localized_boundary(
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = freehand.main(("--resampling", "adaptive", "--locale", "en"))

    assert result == 2
    assert "Freehand diagnostic failed" in capsys.readouterr().err
