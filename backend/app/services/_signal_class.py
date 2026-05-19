"""Centralized signal_class derivation.

signal_class is provenance-based semantic class, not NLP-derived.
Must stay aligned with backend/migrations/021_signal_class.sql backfill UPDATE.

Issue #155, docs/roadmap/2026-05-19-topic-and-signal-class-attack.md.
"""

ALLOWED_SIGNAL_CLASSES = frozenset({
    "reporting",
    "wire",
    "state_media",
    "humanitarian",
    "social_commentary",
    "public_attention",
    "unknown",
})


def derive_signal_class(
    source_family: str | None,
    attribution_method: str | None,
    is_state_media: bool = False,
) -> str:
    """Returns signal_class for a row given its provenance.

    Order matters — most specific rule wins. Must mirror migration 021 CASE.
    """
    if attribution_method == "reddit_public" or source_family == "social":
        return "social_commentary"
    if attribution_method == "reliefweb_ocha" or source_family == "ngo":
        return "humanitarian"
    if is_state_media or source_family == "state":
        return "state_media"
    if source_family == "wire":
        return "wire"
    if source_family in ("gdelt", "rss", "api", "independent"):
        return "reporting"
    return "unknown"
