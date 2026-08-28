"""Application orchestration for the FS-010 local image vertical slice."""

from pathlib import Path

from fourier_sketch.imaging import (
    DenoiseMode,
    ImageFailureCode,
    ImageInputError,
    ImagePreprocessingOptions,
    ImagePreprocessingProvenance,
    ImagePreprocessingResult,
    RasterImage,
    RasterStage,
    autocontrast_grayscale,
    decode_local_image,
    export_raster_png,
    median_denoise,
    threshold_grayscale,
)

_DEFAULT_OPTIONS = ImagePreprocessingOptions()


def preprocess_local_image(
    path: str | Path,
    options: ImagePreprocessingOptions = _DEFAULT_OPTIONS,
) -> ImagePreprocessingResult:
    """Decode and publish all selected transforms only after the whole pipeline succeeds."""
    if not isinstance(options, ImagePreprocessingOptions):
        raise ImageInputError(ImageFailureCode.INVALID_OPTIONS, "preprocessing options are invalid")
    decoded = decode_local_image(path)
    grayscale = decoded.grayscale
    transforms: list[str] = []
    if decoded.provenance.orientation_applied:
        transforms.append("exif_transpose")
    transforms.append("grayscale")
    if options.denoise is DenoiseMode.MEDIAN_3:
        grayscale = median_denoise(grayscale)
        transforms.append(DenoiseMode.MEDIAN_3.value)
    if options.autocontrast:
        grayscale = autocontrast_grayscale(grayscale)
        transforms.append("autocontrast")
    binary = threshold_grayscale(
        grayscale,
        threshold=options.threshold,
        invert=options.invert,
    )
    transforms.append(f"threshold:{options.threshold}")
    if options.invert:
        transforms.append("invert_binary")
    return ImagePreprocessingResult(
        grayscale=grayscale,
        binary=binary,
        provenance=ImagePreprocessingProvenance(
            decode=decoded.provenance,
            transforms=tuple(transforms),
        ),
    )


def select_preprocessing_raster(
    result: ImagePreprocessingResult,
    stage: RasterStage,
) -> RasterImage:
    """Select a named intermediate without treating grayscale and binary as equivalent."""
    if not isinstance(stage, RasterStage):
        raise ImageInputError(ImageFailureCode.INVALID_OPTIONS, "raster stage is invalid")
    return result.grayscale if stage is RasterStage.GRAYSCALE else result.binary


def export_preprocessing_result(
    result: ImagePreprocessingResult,
    stage: RasterStage,
    destination: str | Path,
    *,
    overwrite: bool = False,
) -> None:
    """Export one explicit intermediate as a diagnostic PNG."""
    export_raster_png(
        select_preprocessing_raster(result, stage),
        destination,
        overwrite=overwrite,
    )
