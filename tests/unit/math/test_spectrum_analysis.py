import pytest

from fourier_sketch.domain import (
    Curve,
    DomainValidationError,
    FourierSpectrum,
    Point2D,
    SpectrumOrdering,
)
from fourier_sketch.math import (
    SpectrumAnalysisStatus,
    SpectrumPoint,
    analyze_spectrum,
    curve_to_complex_samples,
    fft_dft,
)


def _fixture() -> tuple[FourierSpectrum, tuple[complex, ...]]:
    curve = Curve(tuple(Point2D(float(i), 0.0) for i in range(8)))
    samples = curve_to_complex_samples(curve)
    return fft_dft(samples), samples


def test_analysis_is_finite_and_traceable() -> None:
    spectrum, samples = _fixture()
    result = analyze_spectrum(spectrum, samples, (1, 3, 8), log_floor=1e-9)
    assert [point.frequency for point in result.points] == list(range(-4, 4))
    assert all(point.log_amplitude == pytest.approx(point.log_amplitude) for point in result.points)
    assert [item.k for item in result.sweep] == [1, 3, 8]
    assert result.sweep[-1].retained_energy_ratio == pytest.approx(1.0)


def test_analysis_rejects_invalid_k_and_explicit_ordering() -> None:
    spectrum, samples = _fixture()
    with pytest.raises(DomainValidationError):
        analyze_spectrum(spectrum, samples, (2, 1))
    with pytest.raises(DomainValidationError):
        analyze_spectrum(spectrum, samples, (1, 9))
    with pytest.raises(DomainValidationError):
        analyze_spectrum(spectrum, samples, (1,), ordering=SpectrumOrdering.EXPLICIT)


def test_analysis_rejects_non_iterable_samples_and_invalid_public_point() -> None:
    spectrum, _samples = _fixture()
    with pytest.raises(DomainValidationError, match="samples must be an iterable"):
        analyze_spectrum(spectrum, None, (1,))  # type: ignore[arg-type]
    with pytest.raises(DomainValidationError):
        SpectrumPoint(0, float("nan"), float("nan"))


def test_resource_limited_sweep_is_explicitly_partial() -> None:
    samples = tuple(0j for _ in range(5000))
    result = analyze_spectrum(fft_dft(samples), samples, (1, 4000))

    assert result.status is SpectrumAnalysisStatus.PARTIAL
    assert result.failure == "reconstruction_budget"
    assert [point.k for point in result.sweep] == [1]


def test_public_analysis_materializes_immutable_collections() -> None:
    spectrum, samples = _fixture()
    valid = analyze_spectrum(spectrum, samples, (1, 8))
    mutable = list(valid.points)

    rebuilt = type(valid)(
        mutable, valid.sweep, valid.ordering, valid.log_floor, valid.sample_count  # type: ignore[arg-type]
    )
    mutable.append(valid.points[0])

    assert rebuilt.points == valid.points
    assert isinstance(rebuilt.points, tuple)
