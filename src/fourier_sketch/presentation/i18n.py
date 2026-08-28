"""Resource-based locale resolution with an algorithmic pseudo-locale."""

import json
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from string import Formatter
from typing import Any

from fourier_sketch.domain import DomainValidationError

DEFAULT_LOCALE = "en"
PSEUDO_LOCALE = "pseudo"
SUPPORTED_LOCALES = frozenset({DEFAULT_LOCALE, PSEUDO_LOCALE})


@dataclass(frozen=True, slots=True)
class LocaleResolution:
    """Observable result of locale precedence and fallback resolution."""

    locale: str
    requested: str | None
    fallback_used: bool


def resolve_locale(
    requested: str | None = None,
    *,
    saved: str | None = None,
    os_hint: str | None = None,
) -> LocaleResolution:
    """Resolve explicit → saved → OS hint → English fallback."""
    first_candidate = requested or saved or os_hint
    for candidate in (requested, saved, os_hint):
        normalized = _normalized_locale(candidate)
        if normalized is not None:
            return LocaleResolution(
                locale=normalized,
                requested=first_candidate,
                fallback_used=(
                    candidate != first_candidate or normalized != _base(first_candidate)
                ),
            )
    return LocaleResolution(
        locale=DEFAULT_LOCALE,
        requested=first_candidate,
        fallback_used=first_candidate is not None and _base(first_candidate) != DEFAULT_LOCALE,
    )


class Translator:
    """Translate resource keys without exposing locale decisions to math/application layers."""

    def __init__(self, locale: str | LocaleResolution = DEFAULT_LOCALE) -> None:
        resolution = locale if isinstance(locale, LocaleResolution) else resolve_locale(locale)
        self._resolution = resolution
        self._catalog = _english_catalog()

    @property
    def resolution(self) -> LocaleResolution:
        return self._resolution

    def text(self, key: str, **values: object) -> str:
        if not isinstance(key, str) or not key:
            raise DomainValidationError("translation key must be a non-empty string")
        template = self._catalog.get(key)
        if template is None:
            return f"[missing:{key}]"
        if self._resolution.locale == PSEUDO_LOCALE:
            template = _pseudo_localize(template)
        try:
            return template.format(**values)
        except (KeyError, ValueError) as error:
            raise DomainValidationError(f"invalid translation values for key {key}") from error


@lru_cache(maxsize=1)
def _english_catalog() -> dict[str, str]:
    resource = resources.files("fourier_sketch.resources").joinpath("en.json")
    try:
        payload: Any = json.loads(resource.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise DomainValidationError("English locale resource is unavailable") from error
    if not isinstance(payload, dict) or any(
        not isinstance(key, str) or not isinstance(value, str) for key, value in payload.items()
    ):
        raise DomainValidationError("English locale resource must map string keys to strings")
    return dict(payload)


def _normalized_locale(value: str | None) -> str | None:
    base = _base(value)
    if base in SUPPORTED_LOCALES:
        return base
    return None


def _base(value: str | None) -> str | None:
    if value is None or not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip().lower().replace("_", "-")
    if normalized == PSEUDO_LOCALE:
        return PSEUDO_LOCALE
    return normalized.split("-", maxsplit=1)[0]


def _pseudo_localize(template: str) -> str:
    parts: list[str] = ["[!! "]
    for literal, field_name, format_spec, conversion in Formatter().parse(template):
        parts.append(_expand_literal(literal))
        if field_name is not None:
            placeholder = "{" + field_name
            if conversion:
                placeholder += f"!{conversion}"
            if format_spec:
                placeholder += f":{format_spec}"
            parts.append(placeholder + "}")
    parts.append(" -- pseudo expansion! !!]")
    return "".join(parts)


def _expand_literal(value: str) -> str:
    vowels = frozenset("aeiouAEIOU")
    return "".join(character * 2 if character in vowels else character for character in value)
