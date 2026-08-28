"""Live CLI → application → Fourier → renderer → PNG product path."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.e2e


def run_cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["MPLBACKEND"] = "Agg"
    return subprocess.run(
        [sys.executable, "-m", "fourier_sketch.cli.diagnostic", *arguments],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
        env=environment,
    )


def test_headless_cli_creates_png_through_live_product_path(tmp_path: Path) -> None:
    output = tmp_path / "epicycles.png"

    result = run_cli(
        "--headless",
        "--output",
        str(output),
        "--frames",
        "12",
        "--harmonics",
        "7",
        "--locale",
        "pseudo",
    )

    assert result.returncode == 0, result.stderr
    payload = output.read_bytes()
    assert payload.startswith(b"\x89PNG\r\n\x1a\n")
    assert payload.endswith(b"IEND\xaeB`\x82")
    assert len(payload) > 10_000
    assert "[!!" in result.stdout


def test_headless_cli_refuses_existing_destination_without_data_loss(tmp_path: Path) -> None:
    output = tmp_path / "existing.png"
    original = b"user-owned-data"
    output.write_bytes(original)

    result = run_cli("--headless", "--output", str(output), "--frames", "1")

    assert result.returncode == 2
    assert output.read_bytes() == original
    assert output.name in result.stderr


def test_invalid_parameters_are_localized_without_leaking_domain_errors(
    tmp_path: Path,
) -> None:
    output = tmp_path / "invalid.png"

    result = run_cli(
        "--headless",
        "--output",
        str(output),
        "--speed",
        "0",
        "--locale",
        "pseudo",
    )

    assert result.returncode == 2
    assert "[!!" in result.stderr
    assert "speed must" not in result.stderr
    assert not output.exists()


def test_unknown_locale_falls_back_to_english_on_failure(tmp_path: Path) -> None:
    output = tmp_path / "fallback.png"

    result = run_cli(
        "--headless",
        "--output",
        str(output),
        "--speed",
        "0",
        "--locale",
        "fr-FR",
    )

    assert result.returncode == 2
    assert "Invalid diagnostic parameters" in result.stderr
    assert "[!!" not in result.stderr
    assert not output.exists()
