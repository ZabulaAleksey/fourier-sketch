"""Immutable indexed-basis decomposition values for FS-033."""

from dataclasses import dataclass
from enum import StrEnum

from ._validation import finite_complex, immutable_tuple, integer
from .basis import BasisKind
from .errors import DomainValidationError


class IndexedNormalization(StrEnum):
    ORTHONORMAL = "orthonormal"


class IndexedOrdering(StrEnum):
    ASCENDING_INDEX = "ascending_index"


def _metadata(
    value: tuple[tuple[str, str], ...], *, field_name: str
) -> tuple[tuple[str, str], ...]:
    metadata = immutable_tuple(value, field_name=field_name)
    normalized: list[tuple[str, str]] = []
    seen: set[str] = set()
    for item in metadata:
        if not isinstance(item, tuple) or len(item) != 2:
            raise DomainValidationError(f"{field_name} entries must be (key, value) pairs")
        key, entry = item
        if not isinstance(key, str) or not key or not isinstance(entry, str):
            raise DomainValidationError(f"{field_name} entries must contain strings")
        if key in seen:
            raise DomainValidationError(f"{field_name} keys must be unique")
        seen.add(key)
        normalized.append((key, entry))
    return tuple(normalized)


def _is_indexed_basis(value: BasisKind) -> bool:
    return value in {BasisKind.DCT_II, BasisKind.WALSH_HADAMARD}


def _analysis_id(term: "IndexedTerm") -> str | None:
    return next((value for key, value in term.provenance if key == "analysis_id"), None)


@dataclass(frozen=True, slots=True)
class IndexedTerm:
    """One complex coefficient in a DCT-II or Walsh-Hadamard basis."""

    value: complex
    index: int
    basis: BasisKind
    provenance: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.basis, BasisKind) or not _is_indexed_basis(self.basis):
            raise DomainValidationError("indexed term basis must be DCT_II or WALSH_HADAMARD")
        object.__setattr__(
            self,
            "value",
            finite_complex(self.value, field_name="indexed term value"),
        )
        object.__setattr__(self, "index", integer(self.index, field_name="indexed term index"))
        if self.index < 0:
            raise DomainValidationError("indexed term index must be non-negative")
        object.__setattr__(self, "provenance", _metadata(self.provenance, field_name="provenance"))

    @property
    def coefficient(self) -> complex:
        return self.value


@dataclass(frozen=True, slots=True)
class IndexedDecomposition:
    """Complete immutable ascending-index decomposition for one indexed basis."""

    terms: tuple[IndexedTerm, ...]
    sample_count: int
    basis: BasisKind
    provenance: tuple[tuple[str, str], ...] = ()
    normalization: IndexedNormalization = IndexedNormalization.ORTHONORMAL
    ordering: IndexedOrdering = IndexedOrdering.ASCENDING_INDEX

    def __post_init__(self) -> None:
        terms = immutable_tuple(self.terms, field_name="indexed decomposition terms")
        count = integer(self.sample_count, field_name="indexed decomposition sample_count")
        if count < 1:
            raise DomainValidationError("indexed sample_count must be positive")
        if self.basis is BasisKind.DCT_II:
            if count > 1024:
                raise DomainValidationError("DCT-II sample_count must be at most 1024")
        elif self.basis is BasisKind.WALSH_HADAMARD:
            if count > 4096 or (count & (count - 1)) != 0:
                raise DomainValidationError(
                    "Walsh sample_count must be a power of two at most 4096"
                )
        else:
            raise DomainValidationError("indexed decomposition basis is unsupported")
        if self.normalization is not IndexedNormalization.ORTHONORMAL:
            raise DomainValidationError("unsupported indexed normalization")
        if self.ordering is not IndexedOrdering.ASCENDING_INDEX:
            raise DomainValidationError("unsupported indexed ordering")
        if len(terms) != count or any(not isinstance(term, IndexedTerm) for term in terms):
            raise DomainValidationError("indexed decomposition must contain one term per sample")
        if tuple(term.index for term in terms) != tuple(range(count)):
            raise DomainValidationError("indexed terms must use ascending index order")
        if any(term.basis is not self.basis for term in terms):
            raise DomainValidationError("indexed terms and decomposition basis must match")
        if len({term.provenance for term in terms}) != 1:
            raise DomainValidationError("indexed terms must share provenance")
        provenance = _metadata(self.provenance, field_name="provenance")
        shared = terms[0].provenance
        ids = tuple(value for key, value in shared if key == "analysis_id")
        public = tuple(item for item in shared if item[0] != "analysis_id")
        if len(ids) != 1 or public != provenance:
            raise DomainValidationError(
                "indexed decomposition provenance must own one analysis identity"
            )
        object.__setattr__(self, "terms", terms)
        object.__setattr__(self, "sample_count", count)
        object.__setattr__(self, "provenance", provenance)

    @property
    def decomposition_id(self) -> str:
        value = _analysis_id(self.terms[0])
        if value is None:  # pragma: no cover - guarded by __post_init__
            raise DomainValidationError("indexed decomposition has no analysis identity")
        return value

    @property
    def coefficients(self) -> tuple[complex, ...]:
        return tuple(term.value for term in self.terms)


@dataclass(frozen=True, slots=True)
class IndexedSelection:
    """Exact owned prefix of an indexed decomposition."""

    terms: tuple[IndexedTerm, ...]
    sample_count: int
    basis: BasisKind
    provenance: tuple[tuple[str, str], ...] = ()
    normalization: IndexedNormalization = IndexedNormalization.ORTHONORMAL
    ordering: IndexedOrdering = IndexedOrdering.ASCENDING_INDEX
    decomposition_id: str | None = None
    source_decomposition: IndexedDecomposition | None = None

    def __post_init__(self) -> None:
        terms = immutable_tuple(self.terms, field_name="indexed selection terms")
        count = integer(self.sample_count, field_name="indexed selection sample_count")
        if count < 1 or not terms or len(terms) > count:
            raise DomainValidationError("indexed selection term count is outside the decomposition")
        if self.basis not in {BasisKind.DCT_II, BasisKind.WALSH_HADAMARD}:
            raise DomainValidationError("indexed selection basis is unsupported")
        if any(not isinstance(term, IndexedTerm) for term in terms):
            raise DomainValidationError("indexed selection terms must be IndexedTerm values")
        if len(terms) != len({term.index for term in terms}):
            raise DomainValidationError("indexed selection indices must be unique")
        if tuple(term.index for term in terms) != tuple(range(len(terms))):
            raise DomainValidationError("indexed selection must be an ascending prefix")
        if any(term.basis is not self.basis for term in terms):
            raise DomainValidationError("indexed selection terms and basis must match")
        if len({term.provenance for term in terms}) != 1:
            raise DomainValidationError("indexed selection terms must share provenance")
        provenance = _metadata(self.provenance, field_name="provenance")
        term_id = _analysis_id(terms[0])
        if self.decomposition_id != term_id:
            raise DomainValidationError("indexed selection decomposition_id does not own its terms")
        source = self.source_decomposition
        if not isinstance(source, IndexedDecomposition):
            raise DomainValidationError("indexed selection requires source decomposition ownership")
        if (
            source.sample_count != count
            or source.basis is not self.basis
            or source.provenance != provenance
            or source.normalization is not self.normalization
            or source.ordering is not self.ordering
            or terms != source.terms[: len(terms)]
        ):
            raise DomainValidationError(
                "indexed selection terms do not belong to source decomposition"
            )
        object.__setattr__(self, "terms", terms)
        object.__setattr__(self, "sample_count", count)
        object.__setattr__(self, "provenance", provenance)

    @property
    def term_count(self) -> int:
        return len(self.terms)

    @property
    def selected_terms(self) -> tuple[IndexedTerm, ...]:
        return self.terms
