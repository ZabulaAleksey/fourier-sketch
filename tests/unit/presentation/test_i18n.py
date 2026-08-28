"""Unit contracts for resource-key locale resolution and pseudo-localization."""

import pytest

from fourier_sketch.presentation import Translator, resolve_locale

pytestmark = pytest.mark.unit


def test_locale_resolution_uses_explicit_saved_os_and_english_fallback() -> None:
    assert resolve_locale("pseudo", saved="en", os_hint="en-US").locale == "pseudo"
    assert resolve_locale(None, saved="en-GB", os_hint="pseudo").locale == "en"
    assert resolve_locale(None, os_hint="en_US").locale == "en"

    fallback = resolve_locale("fr-FR")
    assert fallback.locale == "en"
    assert fallback.requested == "fr-FR"
    assert fallback.fallback_used


def test_english_catalog_formats_user_facing_status() -> None:
    translator = Translator("en")

    assert translator.text("control.play") == "Play"
    assert (
        translator.text(
            "status.summary",
            state="Paused",
            time=0.25,
            harmonics=7,
            speed=1.5,
        )
        == "Paused · t=0.250 · K=7 · speed=1.50\u00d7"
    )


def test_pseudo_locale_expands_literals_and_preserves_format_fields() -> None:
    english = Translator("en").text(
        "status.summary",
        state="Paused",
        time=0.25,
        harmonics=7,
        speed=1.5,
    )
    pseudo = Translator("pseudo").text(
        "status.summary",
        state="Paused",
        time=0.25,
        harmonics=7,
        speed=1.5,
    )

    assert pseudo.startswith("[!! ") and pseudo.endswith("!!]")
    assert "Paused" in pseudo
    assert "0.250" in pseudo
    assert len(pseudo) > len(english) * 1.25


def test_missing_key_is_visibly_marked_in_every_locale() -> None:
    assert Translator("en").text("missing.key") == "[missing:missing.key]"
    assert Translator("pseudo").text("missing.key") == "[missing:missing.key]"
