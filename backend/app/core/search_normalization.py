"""Search query normalization and deterministic expansion for Atlas.

This module stays pure: no database, no FastAPI imports, no external services.
Endpoint code can use it to make search tolerant without making ranking opaque.
"""

from __future__ import annotations

from itertools import permutations
import re
import unicodedata


MAX_VARIANTS = 24

SEARCH_ALIASES: dict[str, list[str]] = {
    "ee uu": ["us", "usa", "united states"],
    "eeuu": ["us", "usa", "united states"],
    "u s": ["us", "usa", "united states"],
    "usa": ["us", "united states"],
    "orthohantavirus": ["hantavirus"],
    "aviones": ["aircraft", "planes"],
    "aeronaves": ["aircraft", "planes"],
    "barcos": ["ships", "vessels", "maritime"],
    "buques": ["ships", "vessels", "maritime"],
}


def normalize_search_text(value: str) -> str:
    """Return a lowercase, accentless, punctuation-normalized query string."""

    decomposed = unicodedata.normalize("NFKD", value)
    accentless = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    lowered = accentless.lower()
    alphanumeric_spaces = re.sub(r"[^a-z0-9]+", " ", lowered)
    return re.sub(r"\s+", " ", alphanumeric_spaces).strip()


def _add_variant(variants: list[str], seen: set[str], value: str) -> None:
    normalized = normalize_search_text(value)
    if normalized and normalized not in seen:
        seen.add(normalized)
        variants.append(normalized)


def _singularize_token(token: str) -> str:
    if token.endswith("virus"):
        return token
    if len(token) > 4 and token.endswith("ies"):
        return f"{token[:-3]}y"
    if len(token) > 4 and token.endswith("es"):
        return token[:-2]
    if len(token) > 3 and token.endswith("s"):
        return token[:-1]
    return token


def build_query_variants(query: str, *, max_variants: int = MAX_VARIANTS) -> list[str]:
    """Build deterministic query variants from most precise to broadest.

    The order matters: callers can use earlier variants as higher-confidence
    matches while still allowing later variants to recover from common mistakes.
    """

    variants: list[str] = []
    seen: set[str] = set()
    normalized = normalize_search_text(query)
    _add_variant(variants, seen, normalized)

    aliases = SEARCH_ALIASES.get(normalized, [])
    for alias in aliases:
        _add_variant(variants, seen, alias)

    tokens = normalized.split()
    if len(tokens) > 1:
        _add_variant(variants, seen, "".join(tokens))

        singular_tokens = [_singularize_token(token) for token in tokens]
        if singular_tokens != tokens:
            _add_variant(variants, seen, " ".join(singular_tokens))

        if 2 <= len(tokens) <= 3:
            for permuted in permutations(tokens):
                _add_variant(variants, seen, " ".join(permuted))

    elif tokens:
        token = tokens[0]
        singular = _singularize_token(token)
        if singular != token:
            _add_variant(variants, seen, singular)
            for alias in SEARCH_ALIASES.get(singular, []):
                _add_variant(variants, seen, alias)

        if token.startswith("ortho") and len(token) > 8:
            _add_variant(variants, seen, token[5:])

    return variants[:max_variants]


def build_like_patterns(query: str) -> list[str]:
    """Return SQL LIKE patterns for normalized variants."""

    return [f"%{variant}%" for variant in build_query_variants(query)]


def should_offer_fuzzy_suggestion(query: str, suggestion: str, score: float) -> bool:
    """Return whether a fuzzy DB hit is strong enough to show as a suggestion."""

    normalized_query = normalize_search_text(query)
    normalized_suggestion = normalize_search_text(suggestion)
    if not normalized_query or not normalized_suggestion:
        return False
    if normalized_query == normalized_suggestion:
        return False
    if len(normalized_query) <= 3:
        return score >= 0.68
    if len(normalized_query) >= 8 and " " in normalized_query:
        return score >= 0.25
    return score >= 0.45
