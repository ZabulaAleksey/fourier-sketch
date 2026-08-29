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
from .matplotlib_skeleton import draw_skeleton_preview, render_skeleton_preview_png
from .matplotlib_skeleton_graph import (
    draw_skeleton_graph_overlay,
    render_skeleton_graph_overlay_png,
)

__all__ = [
    "FreehandControlPanel",
    "FreehandSurface",
    "ImageMvpControlPanel",
    "ImageMvpSurface",
    "create_freehand_surface",
    "create_image_mvp_surface",
    "draw_frame",
    "draw_skeleton_graph_overlay",
    "draw_skeleton_preview",
    "render_frame_png",
    "render_image_mvp_png",
    "render_skeleton_graph_overlay_png",
    "render_skeleton_preview_png",
    "run_freehand_interactive",
    "run_image_mvp_interactive",
    "run_interactive",
]
