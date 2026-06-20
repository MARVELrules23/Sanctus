"""Request-scoped language context.

The frontend sends an `Accept-Language` header (`en` or `es`) on every API
call (driven by the in-app language toggle). A small ASGI middleware stores the
resolved language in a ContextVar so any code path — including AI prompt
builders in other modules — can read it without threading a parameter through
every function signature.

Usage:
    from lang_ctx import get_lang, lang_instruction
    system_prompt += lang_instruction()        # appends a Spanish directive
"""
from __future__ import annotations

from contextvars import ContextVar

current_lang: ContextVar[str] = ContextVar("current_lang", default="en")


def resolve_lang(accept_language: str | None) -> str:
    """Map an Accept-Language header value to a supported language code."""
    al = (accept_language or "").strip().lower()
    if al.startswith("es"):
        return "es"
    if al.startswith("it"):
        return "it"
    return "en"


def get_lang() -> str:
    return current_lang.get()


def lang_instruction() -> str:
    """A directive appended to AI prompts so output is written in the user's
    language. JSON keys stay English; only human-readable values translate."""
    lang = get_lang()
    if lang == "es":
        return (
            " IMPORTANT: Write ALL human-readable text in natural, fluent "
            "Latin American Spanish (español). Keep every JSON key exactly as "
            "specified in English, but translate every string VALUE into Spanish. "
            "Use reverent, pastoral Catholic Spanish."
        )
    if lang == "it":
        return (
            " IMPORTANT: Write ALL human-readable text in natural, fluent "
            "Italian (italiano). Keep every JSON key exactly as "
            "specified in English, but translate every string VALUE into Italian. "
            "Use reverent, pastoral Catholic Italian."
        )
    return ""
