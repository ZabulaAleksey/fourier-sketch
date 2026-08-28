"""Rendering adapters for immutable application frames."""

from .matplotlib_epicycles import draw_frame, render_frame_png, run_interactive
from .matplotlib_freehand import (
    FreehandControlPanel,
    FreehandSurface,
    create_freehand_surface,
    run_freehand_interactive,
)
from .matplotlib_image_mvp import (
    ImageMvpControlPanel,
    ImageMvpSurface,
    create_image_mvp_surface,
    render_image_mvp_png,
    run_image_mvp_interactive,
)

__all__ = [
    "FreehandControlPanel",
    "FreehandSurface",
    "ImageMvpControlPanel",
    "ImageMvpSurface",
    "create_freehand_surface",
    "create_image_mvp_surface",
    "draw_frame",
    "render_frame_png",
    "render_image_mvp_png",
    "run_freehand_interactive",
    "run_image_mvp_interactive",
    "run_interactive",
]
