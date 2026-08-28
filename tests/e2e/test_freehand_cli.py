"""Localized fail-closed evidence for the public freehand CLI boundary."""

import os
import subprocess
import sys

import pytest

pytestmark = pytest.mark.e2e


def run_cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["MPLBACKEND"] = "Agg"
    return subprocess.run(
        [sys.executable, "-m", "fourier_sketch.cli.freehand", *arguments],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
        env=environment,
    )


def test_argparse_failure_uses_pseudo_locale_without_raw_parser_text() -> None:
    result = run_cli("--locale", "pseudo", "--samples", "not-an-integer")

    assert result.returncode == 2
    assert "[!!" in result.stderr
    assert "invalid int value" not in result.stderr
    assert "usage:" not in result.stderr


def test_unknown_locale_failure_falls_back_to_english() -> None:
    result = run_cli("--locale", "fr-FR", "--samples", "not-an-integer")

    assert result.returncode == 2
    assert "Invalid diagnostic parameters" in result.stderr
    assert "[!!" not in result.stderr
