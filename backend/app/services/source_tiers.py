"""Source credibility tiers v1 — #217, spec capability G (product face of P2).

Tiers are LABELS WITH PROVENANCE, never silent filters (No Silent Filtering).
The claim-verification forcing case: a conspiracy amplifier must be labeled
a lower tier than the national met agency contradicting it — and every tier
must be able to say WHY it holds.

Tier ladder (v1, inspectable):
  1 reference   — scientific/meteorological/statistical agencies + fact-checkers
  2 wire        — international news agencies (syndication roots)
  3 mainstream  — established general press (default for known outlets)
  4 unknown     — no signal either way (most of the long tail; honest default)
  5 state       — state-controlled/affiliated media (perspective, not falsity:
                  labeled so the analyst weighs it, mirrors is_state_media)
  6 flagged     — known conspiracy/misinformation amplifiers (spec baseline
                  seeds; grows via the P2 measurement path, never silently)

Ranking consumption (per #217): tier feeds `source_actor_value` priors /
`noise_risk` inputs — no new additive component without a calibration
constraint demanding it. Serving consumption: badge on evidence rows.
"""
from __future__ import annotations

from dataclasses import dataclass

# ── v1 allowlists / flaglists (seeded from spec capability G baselines) ──────
# Domains are matched on the registrable-suffix (endswith after lowercase).

REFERENCE = {
    # meteorological / geophysical / health agencies
    "noaa.gov": "US national oceanic & atmospheric agency",
    "nhc.noaa.gov": "US national hurricane center",
    "usgs.gov": "US geological survey",
    "who.int": "world health organization",
    "ecdc.europa.eu": "EU centre for disease prevention",
    "metoffice.gov.uk": "UK met office",
    "jma.go.jp": "japan meteorological agency",
    "bom.gov.au": "australian bureau of meteorology",
    "reliefweb.int": "UN OCHA humanitarian service",
    "unhcr.org": "UN refugee agency",
    "iaea.org": "international atomic energy agency",
    # fact-checkers (spec claim-verification baseline)
    "aap.com.au": "AAP FactCheck (IFCN signatory)",
    "factcheck.org": "annenberg fact-checker",
    "politifact.com": "poynter fact-checker",
    "fullfact.org": "UK independent fact-checker",
    "afp.com": "AFP (incl. AFP Factuel fact-checking)",
    "rmit.edu.au": "RMIT FactLab (spec baseline)",
}

WIRE = {
    "reuters.com": "international wire agency",
    "apnews.com": "international wire agency",
    "efe.com": "spanish international wire",
    "dpa.com": "german international wire",
    "ansa.it": "italian wire agency",
    "kyodonews.net": "japanese wire agency",
    "anadoluajansi.com.tr": "turkish wire (state-linked: also tier-5 signals)",
}

# Known conspiracy / misinformation amplifiers — spec baseline seeds ONLY;
# additions must come through the P2 measurement path with evidence, never
# ad-hoc. Provenance strings say why each is here.
FLAGGED = {
    "globalresearch.ca": "spec baseline: recurrent conspiracy amplifier",
    "planet-today.com": "spec baseline: recurrent misinformation amplifier",
    "needtoknow.news": "spec baseline: conspiracy aggregator",
    "zerohedge.com": "documented recurrent misinformation amplifier",
    "infowars.com": "documented conspiracy outlet",
    "naturalnews.com": "documented health-misinformation network",
}

# Council R4 N18 (P0, filed three times — R3-1, chip 5560dc0d review, R4):
# the SEALED edition stamped SANA/Xinhua/1tv.ru `tier:"mainstream",
# is_state_media:false` because tier-5 only fired on the ingest flag, which
# the GDELT lane never carries — an asserted False where R3-1 had an honest
# null. This list is the frontend sourceTiers.ts STATE_DOMAINS ported (the
# two lists must not drift: screen and sealed payload DISAGREED live), plus
# 1tv.ru which even the frontend list missed. State = PERSPECTIVE label,
# never a falsity claim (same rule as the flag path below).
STATE = {
    "rt.com": "Russian state broadcaster",
    "sputniknews.com": "Russian state media network",
    "sputnikglobe.com": "Russian state media network",
    "tass.com": "Russian state wire",
    "tass.ru": "Russian state wire",
    "ria.ru": "Russian state wire",
    "1tv.ru": "Russian state Channel One",
    "xinhuanet.com": "Chinese state wire",
    "news.cn": "Chinese state wire (Xinhua)",
    "cgtn.com": "Chinese state broadcaster",
    "globaltimes.cn": "Chinese state tabloid",
    "people.com.cn": "Chinese party organ",
    "chinadaily.com.cn": "Chinese state daily",
    "cctv.com": "Chinese state broadcaster",
    "presstv.ir": "Iranian state broadcaster",
    "irna.ir": "Iranian state wire",
    "tasnimnews.com": "Iranian state-affiliated agency",
    "mehrnews.com": "Iranian state-affiliated agency",
    "trtworld.com": "Turkish state broadcaster",
    "aa.com.tr": "Turkish state wire (Anadolu)",
    "kcna.kp": "North Korean state agency",
    "granma.cu": "Cuban party organ",
    "prensa-latina.cu": "Cuban state wire",
    "telesurtv.net": "Venezuelan-led state network",
    "sana.sy": "Syrian state wire",
}

TIER_LABELS = {
    1: "reference", 2: "wire", 3: "mainstream",
    4: "unknown", 5: "state", 6: "flagged",
}


@dataclass(frozen=True)
class SourceTier:
    tier: int
    label: str
    provenance: str  # WHY this source has this tier — always populated


def _domain_of(source: str | None) -> str:
    s = (source or "").strip().lower()
    if "://" in s:
        s = s.split("://", 1)[1]
    s = s.split("/", 1)[0]
    return s.removeprefix("www.")


def classify_source_tier(
    source: str | None,
    *,
    is_state_media: bool = False,
    source_family: str | None = None,
) -> SourceTier:
    """Tier for one outlet. Order matters: flagged > reference > wire >
    state > family-based mainstream > unknown. State media is a PERSPECTIVE
    label (tier 5), not a falsity claim — and a flagged outlet stays flagged
    even if state-run."""
    dom = _domain_of(source)

    for d, why in FLAGGED.items():
        if dom == d or dom.endswith("." + d):
            return SourceTier(6, TIER_LABELS[6], why)
    for d, why in REFERENCE.items():
        if dom == d or dom.endswith("." + d):
            return SourceTier(1, TIER_LABELS[1], why)
    for d, why in WIRE.items():
        if dom == d or dom.endswith("." + d):
            return SourceTier(2, TIER_LABELS[2], why)
    for d, why in STATE.items():
        if dom == d or dom.endswith("." + d):
            return SourceTier(5, TIER_LABELS[5], why)
    if is_state_media or (source_family or "") == "state":
        return SourceTier(5, TIER_LABELS[5],
                          "state-controlled or state-affiliated outlet "
                          "(ingest is_state_media flag)")
    if (source_family or "") in {"wire"}:
        return SourceTier(2, TIER_LABELS[2], "ingest source_family=wire")
    if (source_family or "") in {"ngo", "gov"}:
        return SourceTier(1, TIER_LABELS[1],
                          f"ingest source_family={source_family} "
                          "(institutional publisher)")
    if (source_family or "") in {"independent", "gdelt"} and dom:
        return SourceTier(3, TIER_LABELS[3],
                          "known press outlet (ingest-registered), no "
                          "adverse or reference signal")
    return SourceTier(4, TIER_LABELS[4],
                      "no credibility signal either way (long-tail outlet)")


def tier_payload(source: str | None, **kw) -> dict:
    """Serving shape: {tier, label, provenance} — attach to evidence rows."""
    t = classify_source_tier(source, **kw)
    return {"tier": t.tier, "label": t.label, "provenance": t.provenance}
