"""Smoke contract for the Stage FS-000 package scaffold."""

import fourier_sketch


def test_package_import_exposes_version() -> None:
    assert fourier_sketch.__version__ == "0.1.0"
