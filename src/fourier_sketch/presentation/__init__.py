"""Presentation boundaries shared by diagnostic and future desktop surfaces."""

from .educational_mode import EducationalCopy, format_educational_copy
from .i18n import LocaleResolution, Translator, resolve_locale

__all__ = [
    "EducationalCopy",
    "LocaleResolution",
    "Translator",
    "format_educational_copy",
    "resolve_locale",
]
