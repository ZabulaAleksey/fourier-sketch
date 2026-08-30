import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image

from fourier_sketch.cli import fft2_image


def test_cli_writes_diagnostic_png(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    output = tmp_path / "fft2.png"
    Image.new("L", (8, 6), 128).save(source)
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "fourier_sketch.cli.fft2_image",
            str(source),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert output.exists() and output.stat().st_size > 0


def test_cli_escapes_bidi_output_basename(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    output = tmp_path / "result\u202egnp.exe.png"
    Image.new("L", (4, 4), 128).save(source)
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "fourier_sketch.cli.fft2_image",
            str(source),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "result\\u202egnp.exe.png" in completed.stdout
    assert "\u202e" not in completed.stdout


def test_cli_failure_does_not_disclose_full_user_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    secret = tmp_path / "private" / "source.png"

    def fail_preprocessing(*_args: object, **_kwargs: object) -> object:
        raise OSError(f"cannot read {secret}")

    monkeypatch.setattr(fft2_image, "preprocess_local_image", fail_preprocessing)

    assert fft2_image.main([str(secret)]) == 2
    captured = capsys.readouterr()
    assert str(secret) not in captured.err
    assert "source.png" in captured.err
