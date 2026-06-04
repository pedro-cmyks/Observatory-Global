from __future__ import annotations

from typing import Any

NOTE_SOURCE = "extractive-v1"


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _clean_text(value: Any, limit: int = 180) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.split())
    if not cleaned:
        return None
    return cleaned[:limit].rstrip()


def _format_count(value: int) -> str:
    return f"{value:,}"


def _join(items: list[str], fallback: str) -> str:
    clean = [item for item in items if item]
    if not clean:
        return fallback
    if len(clean) == 1:
        return clean[0]
    if len(clean) == 2:
        return f"{clean[0]} and {clean[1]}"
    return f"{', '.join(clean[:-1])}, and {clean[-1]}"


def _select_evidence(
    samples: list[dict[str, Any]],
    limit: int = 3,
) -> tuple[list[dict[str, str]], int]:
    snippet_count = sum(1 for sample in samples if _clean_text(sample.get("snippet")))
    ranked = sorted(
        samples,
        key=lambda sample: 0 if _clean_text(sample.get("snippet")) else 1,
    )
    selected: list[dict[str, str]] = []
    seen_sources: set[str] = set()
    for sample in ranked:
        source = _clean_text(sample.get("source"), 80) or "unknown source"
        if source in seen_sources and len(seen_sources) < limit:
            continue
        text = _clean_text(sample.get("snippet")) or _clean_text(sample.get("headline"))
        if not text:
            continue
        selected.append({"source": source, "text": text})
        seen_sources.add(source)
        if len(selected) >= limit:
            break
    return selected, snippet_count


def build_thread_narrative_note(thread: dict[str, Any]) -> dict[str, Any] | None:
    label = _clean_text(thread.get("label") or thread.get("summary"), 120)
    signal_count = int(thread.get("signal_count") or 0)
    if not label or signal_count <= 0:
        return None

    changed_10h = int(thread.get("changed_10h") or 0)
    source_count = int(thread.get("source_count") or 0)
    country_count = int(thread.get("country_count") or 0)
    countries = [
        str(v)
        for v in (_as_list(thread.get("top_country_names")) or _as_list(thread.get("top_countries")))
        if v
    ]
    source_mix = thread.get("source_mix") if isinstance(thread.get("source_mix"), dict) else {}
    sources = [
        str(v)
        for v in (_as_list(thread.get("top_sources")) or _as_list(source_mix.get("top_sources")))
        if v
    ]
    quality_meta = thread.get("quality") if isinstance(thread.get("quality"), dict) else {}
    noise_rate = quality_meta.get("noise_rate")
    evidence, snippet_count = _select_evidence(
        [s for s in _as_list(thread.get("evidence_samples")) if isinstance(s, dict)]
    )

    country_phrase = _join(countries[:3], "the visible geography")
    source_phrase = _join(sources[:3], "the visible source set")
    lede = f"{label} is moving across {country_phrase}."

    if changed_10h > 0:
        movement_delta = f"{changed_10h:,}-signal rise"
    elif changed_10h < 0:
        movement_delta = f"{abs(changed_10h):,}-signal drop"
    else:
        movement_delta = "flat short-term movement"
    movement = (
        f"The thread has {_format_count(signal_count)} signals, a {movement_delta} in the last 10 hours, "
        f"across {country_count or len(countries) or 1} countries and {source_count or len(sources) or 1} sources."
    )

    if evidence:
        evidence_bits = [f"{item['source']}: {item['text']}" for item in evidence]
        evidence_text = "; ".join(evidence_bits)
        evidence_sentence = (
            f"The strongest visible support comes from {source_phrase}, "
            f"with evidence including {evidence_text}."
        )
    else:
        evidence_sentence = (
            f"The strongest visible support comes from {source_phrase}, "
            "but representative evidence samples are still sparse."
        )

    caveats: list[str] = []
    if snippet_count == 0:
        caveats.append("evidence is headline-heavy")
    if source_count and source_count < 2:
        caveats.append("source diversity is thin")
    if country_count and country_count < 2:
        caveats.append("geographic spread is narrow")
    if isinstance(noise_rate, (int, float)) and noise_rate >= 0.2:
        caveats.append("the cluster carries elevated noise")
    if quality_meta.get("source_flags", {}).get("aggregator_dominant"):
        caveats.append("aggregator-heavy sourcing may distort attention")
    if quality_meta.get("geo_flags", {}).get("unresolved_country_code"):
        caveats.append("some geography is unresolved")

    if signal_count < 10 or source_count < 2:
        quality = "thin"
    elif caveats:
        quality = "provisional"
    else:
        quality = "strong"

    caveat = None
    if caveats:
        caveat = f"Treat this as {quality} because {', '.join(caveats)}."

    return {
        "lede": lede,
        "movement": movement,
        "evidence": evidence_sentence,
        "caveat": caveat,
        "quality": quality,
        "source": NOTE_SOURCE,
    }
