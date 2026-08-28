"""Rendering adapters for immutable application frames."""

from .matplotlib_epicycles import draw_frame, render_frame_png, run_interactive
from .matplotlib_freehand import (
    FreehandSurface,
    create_freehand_surface,
    run_freehand_interactive,
)

__all__ = [
    "FreehandSurface",
    "create_freehand_surface",
    "draw_frame",
    "render_frame_png",
    "run_freehand_interactive",
    "run_interactive",
]
