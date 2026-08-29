"""Source-run entry point for the FS-021 PySide6 desktop slice."""

import argparse

from fourier_sketch.ui import run_desktop


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Fourier Sketch desktop workflow.")
    parser.add_argument("--locale", choices=("en", "pseudo"), default="en")
    return run_desktop(locale=parser.parse_args().locale)


if __name__ == "__main__":
    raise SystemExit(main())
