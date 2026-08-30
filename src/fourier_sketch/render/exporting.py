"""FS-022 PNG/GIF adapters over immutable application export state."""

from __future__ import annotations

import json
from collections.abc import Callable
from io import BytesIO
from pathlib import Path
from typing import Any, cast

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from PIL import Image

from fourier_sketch.application.exporting import (
    EXPORT_SCHEMA_VERSION,
    AnimationExportPlan,
    atomic_publish_bytes,
    iter_animation_frames,
)
from fourier_sketch.domain import CoefficientSelection, DomainValidationError
from fourier_sketch.presentation import Translator

from .matplotlib_epicycles import draw_frame


def render_spectrum_png(
    selection: CoefficientSelection,
    output: Path,
    translator: Translator,
    *,
    overwrite: bool = False,
    cancelled: Callable[[], bool] | None = None,
) -> Path:
    """Render the current ordered coefficient amplitudes to an atomic PNG."""

    if not isinstance(selection, CoefficientSelection):
        raise DomainValidationError("spectrum PNG requires a CoefficientSelection")
    if not isinstance(translator, Translator):
        raise DomainValidationError("spectrum PNG requires a Translator")
    figure = Figure(figsize=(8.0, 5.0), layout="constrained")
    canvas = FigureCanvasAgg(figure)
    axes = figure.subplots()
    frequencies = tuple(item.frequency for item in selection.coefficients)
    amplitudes = tuple(item.amplitude for item in selection.coefficients)
    axes.stem(frequencies, amplitudes, basefmt=" ")
    axes.set_title(translator.text("export.spectrum.title"))
    axes.set_xlabel(translator.text("export.spectrum.frequency"))
    axes.set_ylabel(translator.text("export.spectrum.amplitude"))
    axes.grid(True, linewidth=0.4, alpha=0.3)
    encoded = BytesIO()
    cast(Any, canvas).print_png(encoded)
    return atomic_publish_bytes(
        output,
        encoded.getvalue(),
        suffix=".png",
        overwrite=overwrite,
        cancelled=cancelled,
    )


def export_animation_gif(
    plan: AnimationExportPlan,
    output: Path,
    translator: Translator,
    *,
    overwrite: bool = False,
    cancelled: Callable[[], bool] | None = None,
    progress: Callable[[int], None] | None = None,
) -> Path:
    """Encode a bounded GIF whose metadata records the actual frame endpoints."""

    if not isinstance(plan, AnimationExportPlan):
        raise DomainValidationError("GIF export requires an AnimationExportPlan")
    if not isinstance(translator, Translator):
        raise DomainValidationError("GIF export requires a Translator")
    if progress is not None and not callable(progress):
        raise DomainValidationError("progress must be callable")

    images: list[Image.Image] = []
    endpoints: list[tuple[float, float]] = []
    figure = Figure(figsize=(6.0, 6.0), dpi=80, layout="constrained")
    canvas = FigureCanvasAgg(figure)
    typed_canvas = cast(Any, canvas)
    axes = figure.subplots()
    for index, frame in enumerate(iter_animation_frames(plan, cancelled=cancelled), start=1):
        draw_frame(axes, frame, translator)
        typed_canvas.draw()
        width, height = canvas.get_width_height()
        rgba = Image.frombuffer(
            "RGBA",
            (width, height),
            typed_canvas.buffer_rgba(),
            "raw",
            "RGBA",
            0,
            1,
        ).copy()
        images.append(rgba.convert("P", palette=Image.Palette.ADAPTIVE, colors=256))
        endpoints.append((frame.chain.endpoint.x, frame.chain.endpoint.y))
        if progress is not None:
            progress(round(index * 100 / plan.frame_count))

    metadata = json.dumps(
        {
            "schema": "fourier-sketch.epicycle-animation",
            "version": EXPORT_SCHEMA_VERSION,
            "frame_count": plan.frame_count,
            "frame_duration_ms": plan.frame_duration_ms,
            "sample_count": plan.frame.selection.sample_count,
            "ordering": plan.frame.selection.ordering.value,
            "frequencies": list(plan.frame.selection.frequencies),
            "endpoints": endpoints,
        },
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("ascii")
    if not images:
        raise DomainValidationError("GIF export produced no frames")
    encoded = BytesIO()
    images[0].save(
        encoded,
        format="GIF",
        save_all=True,
        append_images=images[1:],
        duration=plan.frame_duration_ms,
        loop=0,
        disposal=2,
        comment=metadata,
    )
    return atomic_publish_bytes(
        output,
        encoded.getvalue(),
        suffix=".gif",
        overwrite=overwrite,
        cancelled=cancelled,
    )
