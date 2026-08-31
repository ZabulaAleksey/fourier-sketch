"""Immutable basis-selection and Haar decomposition domain values."""

from dataclasses import dataclass
from enum import StrEnum

from ._validation import finite_complex, immutable_tuple, integer
from .errors import DomainValidationError


class BasisKind(StrEnum):
    """User-selectable curve decomposition bases."""

    FOURIER_EPICYCLE = "fourier_epicycle"
    HAAR_WAVELET = "haar_wavelet"


class HaarTermKind(StrEnum):
    """The two coefficient roles in an orthonormal Haar decomposition."""

    SCALING = "scaling"
    DETAIL = "detail"


class HaarNormalization(StrEnum):
    """Normalization used by the project Haar transform."""

    ORTHONORMAL_1_OVER_SQRT2 = "orthonormal_1_over_sqrt2"


class HaarOrdering(StrEnum):
    """Stable public order of Haar terms."""

    ROOT_COARSE_TO_FINE = "root_coarse_to_fine"


def _metadata(
    value: tuple[tuple[str, str], ...], *, field_name: str
) -> tuple[tuple[str, str], ...]:
    metadata = immutable_tuple(value, field_name=field_name)
    result: list[tuple[str, str]] = []
    seen: set[str] = set()
    for item in metadata:
        if not isinstance(item, tuple) or len(item) != 2:
            raise DomainValidationError(f"{field_name} entries must be (key, value) pairs")
        key, entry_value = item
        if not isinstance(key, str) or not key:
            raise DomainValidationError(f"{field_name} keys must be non-empty strings")
        if not isinstance(entry_value, str):
            raise DomainValidationError(f"{field_name} values must be strings")
        if key in seen:
            raise DomainValidationError(f"{field_name} keys must be unique")
        seen.add(key)
        result.append((key, entry_value))
    return tuple(result)


@dataclass(frozen=True, slots=True)
class HaarTerm:
    """One immutable scaling or detail coefficient with scale/location provenance."""

    value: complex
    scale: int
    location: int
    kind: HaarTermKind = HaarTermKind.DETAIL
    basis: BasisKind = BasisKind.HAAR_WAVELET
    provenance: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.basis, BasisKind):
            raise DomainValidationError("Haar term basis must be a BasisKind")
        if self.basis is not BasisKind.HAAR_WAVELET:
            raise DomainValidationError("Haar terms require the HAAR_WAVELET basis")
        if not isinstance(self.kind, HaarTermKind):
            raise DomainValidationError("Haar term kind must be a HaarTermKind")
        scale = integer(self.scale, field_name="Haar term scale")
        location = integer(self.location, field_name="Haar term location")
        if scale < 0 or location < 0:
            raise DomainValidationError("Haar term scale and location must be non-negative")
        if self.kind is HaarTermKind.SCALING and location != 0:
            raise DomainValidationError("Haar scaling term location must be zero")
        object.__setattr__(self, "value", finite_complex(self.value, field_name="Haar term value"))
        object.__setattr__(self, "scale", scale)
        object.__setattr__(self, "location", location)
        object.__setattr__(self, "provenance", _metadata(self.provenance, field_name="provenance"))

    @property
    def level(self) -> int:
        """Alias for scale terminology used in the mathematical documentation."""
        return self.scale

    @property
    def coefficient(self) -> complex:
        return self.value


@dataclass(frozen=True, slots=True)
class HaarDecomposition:
    """Complete canonical orthonormal Haar coefficient array."""

    terms: tuple[HaarTerm, ...]
    sample_count: int
    basis: BasisKind = BasisKind.HAAR_WAVELET
    provenance: tuple[tuple[str, str], ...] = ()
    normalization: HaarNormalization = HaarNormalization.ORTHONORMAL_1_OVER_SQRT2
    ordering: HaarOrdering = HaarOrdering.ROOT_COARSE_TO_FINE

    def __post_init__(self) -> None:
        terms = immutable_tuple(self.terms, field_name="Haar decomposition terms")
        count = integer(self.sample_count, field_name="Haar decomposition sample_count")
        if count < 1 or count > 4096 or (count & (count - 1)) != 0:
            raise DomainValidationError(
                "Haar sample_count must be 1 or a power of two at most 4096"
            )
        if not isinstance(self.basis, BasisKind) or self.basis is not BasisKind.HAAR_WAVELET:
            raise DomainValidationError("Haar decomposition basis must be HAAR_WAVELET")
        if self.normalization is not HaarNormalization.ORTHONORMAL_1_OVER_SQRT2:
            raise DomainValidationError("unsupported Haar normalization")
        if self.ordering is not HaarOrdering.ROOT_COARSE_TO_FINE:
            raise DomainValidationError("unsupported Haar ordering")
        if len(terms) != count or any(not isinstance(term, HaarTerm) for term in terms):
            raise DomainValidationError("Haar decomposition must contain one term per sample")
        levels = count.bit_length() - 1
        expected: tuple[tuple[HaarTermKind, int, int], ...] = (
            (HaarTermKind.SCALING, levels, 0),
            *(
                (HaarTermKind.DETAIL, scale, location)
                for scale in range(levels - 1, -1, -1)
                for location in range(1 << (levels - scale - 1))
            )
        )
        actual = tuple((term.kind, term.scale, term.location) for term in terms)
        if actual != expected:
            raise DomainValidationError("Haar terms must use root-scaling/coarse-to-fine order")
        if any(term.basis is not self.basis for term in terms):
            raise DomainValidationError("Haar terms and decomposition basis must match")
        term_provenance = {term.provenance for term in terms}
        if len(term_provenance) > 1:
            raise DomainValidationError("Haar decomposition terms must share provenance")
        provenance = _metadata(self.provenance, field_name="provenance")
        shared_provenance = terms[0].provenance
        analysis_ids = tuple(
            value for key, value in shared_provenance if key == "analysis_id"
        )
        public_provenance = tuple(
            item for item in shared_provenance if item[0] != "analysis_id"
        )
        if (
            len(analysis_ids) != 1
            or not analysis_ids[0]
            or public_provenance != provenance
        ):
            raise DomainValidationError(
                "Haar decomposition provenance must own one analysis identity"
            )
        object.__setattr__(self, "terms", terms)
        object.__setattr__(self, "sample_count", count)
        object.__setattr__(self, "provenance", provenance)

    @property
    def scaling_term(self) -> HaarTerm:
        return self.terms[0]

    @property
    def detail_terms(self) -> tuple[HaarTerm, ...]:
        return self.terms[1:]

    @property
    def coefficients(self) -> tuple[complex, ...]:
        return tuple(term.value for term in self.terms)

    @property
    def decomposition_id(self) -> str | None:
        for key, value in self.terms[0].provenance:
            if key == "analysis_id":
                return value
        return None


@dataclass(frozen=True, slots=True)
class HaarSelection:
    """Immutable ordered prefix of a complete Haar decomposition."""

    terms: tuple[HaarTerm, ...]
    sample_count: int
    basis: BasisKind = BasisKind.HAAR_WAVELET
    provenance: tuple[tuple[str, str], ...] = ()
    normalization: HaarNormalization = HaarNormalization.ORTHONORMAL_1_OVER_SQRT2
    ordering: HaarOrdering = HaarOrdering.ROOT_COARSE_TO_FINE
    decomposition_id: str | None = None
    source_decomposition: HaarDecomposition | None = None

    def __post_init__(self) -> None:
        terms = immutable_tuple(self.terms, field_name="Haar selection terms")
        count = integer(self.sample_count, field_name="Haar selection sample_count")
        if (
            count < 1
            or count > 4096
            or (count & (count - 1)) != 0
            or len(terms) < 1
            or len(terms) > count
        ):
            raise DomainValidationError("Haar selection term count is outside the decomposition")
        if self.basis is not BasisKind.HAAR_WAVELET:
            raise DomainValidationError("Haar selection basis must be HAAR_WAVELET")
        if self.normalization is not HaarNormalization.ORTHONORMAL_1_OVER_SQRT2:
            raise DomainValidationError("unsupported Haar normalization")
        if self.ordering is not HaarOrdering.ROOT_COARSE_TO_FINE:
            raise DomainValidationError("unsupported Haar ordering")
        if any(not isinstance(term, HaarTerm) for term in terms):
            raise DomainValidationError("Haar selection terms must be HaarTerm values")
        if tuple(term for term in terms) != terms:
            raise DomainValidationError("Haar selection terms must be immutable")
        if terms[0].kind is not HaarTermKind.SCALING:
            raise DomainValidationError("Haar selection must start with root scaling")
        if any(term.basis is not self.basis for term in terms):
            raise DomainValidationError("Haar terms and selection basis must match")
        if len({term.provenance for term in terms}) > 1:
            raise DomainValidationError("Haar selection terms must share provenance")
        levels = count.bit_length() - 1
        expected_prefix = (
            (HaarTermKind.SCALING, levels, 0),
            *(
                (HaarTermKind.DETAIL, scale, location)
                for scale in range(levels - 1, -1, -1)
                for location in range(1 << (levels - scale - 1))
            ),
        )[: len(terms)]
        if tuple((term.kind, term.scale, term.location) for term in terms) != expected_prefix:
            raise DomainValidationError("Haar selection must be a canonical term prefix")
        term_id = next(
            (value for key, value in terms[0].provenance if key == "analysis_id"),
            None,
        )
        if self.decomposition_id is not None and (
            not isinstance(self.decomposition_id, str)
            or not self.decomposition_id
            or self.decomposition_id != term_id
        ):
            raise DomainValidationError("Haar selection decomposition_id does not own its terms")
        source = self.source_decomposition
        if source is not None:
            if not isinstance(source, HaarDecomposition):
                raise DomainValidationError("Haar source_decomposition must be a HaarDecomposition")
            if (
                source.sample_count != count
                or source.basis is not self.basis
                or source.normalization is not self.normalization
                or source.ordering is not self.ordering
                or source.provenance != self.provenance
                or tuple(terms) != source.terms[: len(terms)]
            ):
                raise DomainValidationError(
                    "Haar selection terms do not belong to source decomposition"
                )
            if self.decomposition_id != source.decomposition_id:
                raise DomainValidationError("Haar selection decomposition_id does not match source")
        else:
            raise DomainValidationError("Haar selection requires source decomposition ownership")
        object.__setattr__(self, "terms", terms)
        object.__setattr__(self, "sample_count", count)
        object.__setattr__(self, "provenance", _metadata(self.provenance, field_name="provenance"))

    @property
    def term_count(self) -> int:
        return len(self.terms)

    @property
    def selected_terms(self) -> tuple[HaarTerm, ...]:
        return self.terms
