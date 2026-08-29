import subprocess
import sys
from pathlib import Path

from PIL import Image


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
