# Attention–Coverage Divergence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the parked silent-risk detector with a measured attention–coverage divergence metric: type Google-Trends public attention into Atlas's own taxonomy, compare its share against coverage share per `(parent_domain, country)`, and surface the divergence on three surfaces — never claiming the press is silent.

**Architecture:** Heavy compute runs on the M1 (e5 embedding + whitening + corpus matching) and writes one row per `(country, keyword, day)` into a new `public_attention_typed` table; the API serves a pure read plus share arithmetic. All decision logic lives in two pure, unit-tested modules so thresholds can be re-measured without touching the router. Mirrors the existing `silent_risk.py` pure-helpers + thin-router pattern.

**Tech Stack:** Python 3 / FastAPI / asyncpg / Postgres (Supabase), numpy, multilingual-e5 via `mlvenv` on the M1, Atlas's global whitening artifact (`backend/app/data/e5_whitening.npz`), React + vanilla CSS + vitest on the frontend.

**Spec:** `docs/superpowers/specs/2026-07-22-attention-coverage-divergence-design.md`

---

## ⛔⛔ PLAN CLOSED — Task 0 ran and killed the metric (2026-07-22)

Task 0 executed. ρ(divergence_real, divergence_placebo) = **0.714**, at the
pre-registered kill threshold of 0.7. Full result:
`docs/research/silent-risk/2026-07-22-domain-placebo.md`. Spec is CLOSED.

**Do not execute any task in this plan.** Tasks 1–3 and 7 remain *correct* code
if ever wanted for another purpose, but there is no longer a feature for them to
serve. The plan is kept as the record.

---

## ⛔ STOP — this plan was blocked (2026-07-22, superseded by the line above)

The spec was undercut by its own measurement the same day it was written. Read
spec §0 before touching anything. A placebo control shows `coverage_count` is a
**lexical-match rate, not a coverage measurement** (matching keywords against
press from *before* they trended yields 42.7–59.4% "silent"; 61% of the bug
fix's rescues are "covered" by pre-trend press), and the silent set's 22.5%
story base rate is **not significantly different** from the covered set's 15.8%.

**Do NOT run Tasks 4–6 or 8–15.** Only these survive as written:

- **Task 1, 2, 3** — pure modules. Correct and useful regardless; Task 1 in
  particular freezes real bugs as tests.
- **Task 7** — delete `_INFO_DESERT_FLOOR` and retire `/silent-risks`. Measured
  inverted; the deletion stands on its own evidence.

**Do this instead, first — Task 0.**

### Task 0: Placebo the DOMAIN-LEVEL metric

The placebo tested per-keyword coverage. The metric this plan builds aggregates
to `(parent_domain, country)` shares, which was never tested. Test it before
building it.

- [ ] **Step 1: Compute `divergence_table` twice for the same day** — once with
      coverage from the current window, once with coverage from press published
      5–7 days *before* the trend window. Same attention side both times.
- [ ] **Step 2: Correlate the two divergence vectors** across all countries.
      Run: Spearman ρ over the per-`(domain, country)` divergence values.
- [ ] **Step 3: Read the verdict honestly.**
      - ρ high (≳0.7) → domain divergence is the same with fake coverage as with
        real coverage. **The metric is dead. Close the spec, do not fix it.**
      - ρ low → domain aggregation survives what per-keyword matching did not;
        record the number, unblock the spec, and continue to Task 1.
- [ ] **Step 4: Write the result** to
      `docs/research/silent-risk/2026-XX-XX-domain-placebo.md` and update the
      spec status either way.

---

## Blocking dependency

The GDELT HTML-entity fix (separate task, in flight) changes the corpus every
number here is computed on. **Tasks 1–8 may proceed now** — they are pure logic,
schema, and plumbing whose correctness does not depend on the corpus. **Task 9
(threshold calibration) must run after the entity fix lands** and is the gate for
Tasks 10–12 (surfaces).

Until then, `unescape_fold()` in Task 1 does the unescaping at read time, so the
pipeline is correct even on the un-fixed corpus.

---

## File structure

| File | Responsibility |
|---|---|
| `backend/app/services/attention_match.py` | **Create.** Pure text layer: unescape+script-safe fold, script detection, tokenisation, idf-coverage matching. No DB, no network. |
| `backend/app/services/attention_divergence.py` | **Pure decision layer.** Domain shares, divergence, `is_new`, rule noise classes, tray reason codes. No DB, no network. |
| `backend/app/services/attention_anchors.py` | **Create.** The negative-anchor set + anchor-text builder from `atlas_topics` seed rows. |
| `backend/migrations/090_public_attention_typed.sql` | **Create.** The precomputed table. |
| `backend/scripts/type_public_attention.py` | **Create.** M1 job: embed → whiten → argmax → match corpus → upsert. |
| `backend/app/routers/attention_threads.py` | **Modify.** Add `GET /api/v2/attention/divergence`; retire `/silent-risks`. |
| `backend/app/services/silent_risk.py` | **Delete** in Task 8 (superseded). |
| `frontend-v2/src/lib/attentionDivergence.ts` | **Create.** Pure client shaping + labels. |
| `frontend-v2/src/components/BriefNewspaper.tsx` | **Modify.** Country band + global section. |
| `frontend-v2/src/components/AnomalyPanel.tsx` | **Modify.** Restructure PUBLIC ATTENTION to the interpreted view. |
| `scripts/run-atlas-topic-classifier.sh` | **Modify.** New Step 6 wiring. |

---

## Task 1: Pure text-matching layer

**Files:**
- Create: `backend/app/services/attention_match.py`
- Test: `backend/tests/test_attention_match.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_attention_match.py
"""Pure text layer for attention↔coverage matching.

Freezes the three instrument bugs found on 2026-07-22 so they cannot return:
  B1 HTML entities (46.6% of the press corpus, 100% the GDELT lane)
  B2 the index gate (exact-token index + substring verify = morphology misses)
  B3 the all-tokens conjunction (abbreviations guarantee a miss)
"""
from app.services.attention_match import (
    IdfIndex, keyword_tokens, script_of, unescape_fold,
)


def test_unescape_fold_decodes_html_entities():
    # B1: the GDELT lane stores 'hurac&#xE1;n'; without unescape the word
    # cannot exist and the topic reads as silent.
    assert unescape_fold("Se forma hurac&#xE1;n Fausto") == "se forma huracan fausto"


def test_unescape_fold_strips_latin_diacritics():
    assert unescape_fold("Çalhanoğlu") == "calhanoglu"


def test_unescape_fold_preserves_indic_and_thai_combining_marks():
    # The old fold used re.sub(r'[^\w\s]') and \w excludes category Mn, so
    # Devanagari/Thai vowels were deleted outright.
    assert "ि" in unescape_fold("दिल्ली में बारिश")   # ि survives
    assert "้" in unescape_fold("ฝนตกหนักกรุงเทพ")     # ้ survives


def test_script_of_detects_no_space_scripts():
    assert script_of("台灣颱風假") == "HAN"
    assert script_of("ฝนตก") == "THAI"
    assert script_of("earthquake dubbo") == "LATIN"
    assert script_of("разлив нефти") == "CYRILLIC"


def test_keyword_tokens_handles_no_space_scripts():
    # No whitespace words: the whole string is the token, min length 2.
    assert keyword_tokens("台灣颱風假", "HAN") == ["台灣颱風假"]
    # Latin: stopwords and short tokens dropped, min length 3.
    assert keyword_tokens("the flood in nogales", "LATIN") == ["flood", "nogales"]


def test_idf_index_matches_through_morphology():
    # B2: the corpus only ever contains 'predicciones'; an exact-token index
    # returns an empty candidate set and scores the keyword silent.
    idx = IdfIndex(["Las predicciones del clima para Sonora"])
    n, cov = idx.coverage("prediccion", "LATIN")
    assert n == 1
    assert cov == 1.0


def test_idf_index_matches_entity_encoded_headline():
    idx = IdfIndex(["Se forma hurac&#xE1;n Fausto en el Pac&#xED;fico"])
    n, _cov = idx.coverage("huracan", "LATIN")
    assert n == 1


def test_idf_index_partial_coverage_is_below_threshold():
    # B3: 'nottm forest vs blackburn rovers' — the abbreviation is never in a
    # headline, so coverage must be partial, not zero and not full.
    idx = IdfIndex(["Blackburn Rovers squad for the Portugal friendly"])
    n, cov = idx.coverage("nottm forest blackburn rovers", "LATIN")
    assert 0.0 < cov < 1.0
    assert n == 0  # below the 0.60 keep threshold


def test_idf_index_reports_zero_for_genuinely_absent_keyword():
    idx = IdfIndex(["Completely unrelated headline about football"])
    n, cov = idx.coverage("volcano eruption", "LATIN")
    assert n == 0
    assert cov == 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_attention_match.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.attention_match'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/services/attention_match.py
"""Pure text layer for attention↔coverage matching (no DB, no network).

Matching is GENEROUS on purpose: it biases toward "covered", so the detector
under-reports divergence rather than fabricating it.

Three bugs measured on prod 2026-07-22 are fixed here by construction:
  B1 46.6% of press headlines store HTML numeric character references
     ('hurac&#xE1;n') — entirely the GDELT lane. Always unescape first.
  B2 an inverted index keyed on exact whitespace tokens, verified by substring,
     misses morphology ('prediccion' vs 'predicciones') and — worse — picking
     the rarest token by len(index[t]) picks the ABSENT token, since missing
     means length 0. Character trigrams fix both.
  B3 requiring ALL tokens is too strict (abbreviations). Use idf-weighted
     coverage with a measured threshold instead.
"""
from __future__ import annotations

import html
import math
import re
import unicodedata
from collections import defaultdict

#: Scripts written without inter-word spaces — tokenisation must not split them.
NO_SPACE_SCRIPTS = ("HAN", "HIRAGANA", "KATAKANA", "THAI", "HANGUL")

#: Measured operating point (2026-07-22): precision 0.76 / recall 0.65 against
#: 60 hand-adjudicated items. Re-measure after the GDELT entity fix lands.
IDF_COVERAGE_KEEP = 0.60

_STOPWORDS = {
    "the", "and", "for", "with", "from", "new", "vs", "de", "la", "el", "los",
    "las", "del", "en", "y", "il", "der", "die", "das", "und", "von", "im",
    "le", "les", "du", "des", "et", "da", "do", "no", "na", "em", "of", "to",
    "in", "on", "at", "is", "are", "was", "today", "live", "news", "hoy", "x",
}


def script_of(text: str) -> str:
    """Unicode script of the first alphabetic character, or LATIN if none."""
    for ch in text or "":
        if not ch.isalpha():
            continue
        try:
            name = unicodedata.name(ch).split()[0]
        except ValueError:
            continue
        return name
    return "LATIN"


def unescape_fold(text: str) -> str:
    """HTML-unescape, lowercase, drop Latin/Greek/Cyrillic diacritics, and
    replace punctuation with spaces — WITHOUT shredding Indic/Thai/Arabic,
    whose vowels are combining marks above U+0800."""
    decoded = html.unescape(text or "")
    out: list[str] = []
    for ch in unicodedata.normalize("NFKD", decoded):
        if unicodedata.category(ch) == "Mn":
            out.append(ch if ord(ch) > 0x0800 else "")
            continue
        out.append(ch if (ch.isalnum() or ch.isspace()) else " ")
    return re.sub(r"\s+", " ", "".join(out).lower()).strip()


def keyword_tokens(folded: str, script: str) -> list[str]:
    """Significant tokens of an already-folded keyword."""
    if script in NO_SPACE_SCRIPTS:
        joined = folded.replace(" ", "")
        return [joined] if len(joined) >= 2 else []
    return [t for t in folded.split()
            if len(t) >= 3 and t not in _STOPWORDS]


class IdfIndex:
    """Folded headline corpus + a character-trigram candidate index.

    Trigrams are superset-safe: any headline containing token T contains every
    trigram of T, so intersecting the trigram postings never loses a true hit
    while keeping the substring verification cheap.
    """

    def __init__(self, headlines: list[str]) -> None:
        self.folded = [unescape_fold(h) for h in headlines]
        self.trigrams: dict[str, set[int]] = defaultdict(set)
        self.doc_freq: dict[str, int] = defaultdict(int)
        for i, fh in enumerate(self.folded):
            for g in {fh[j:j + 3] for j in range(max(len(fh) - 2, 0))}:
                if " " not in g:
                    self.trigrams[g].add(i)
            for t in set(fh.split()):
                self.doc_freq[t] += 1
        self.n_docs = max(len(self.folded), 1)

    def _candidates(self, token: str) -> set[int]:
        grams = [token[j:j + 3] for j in range(max(len(token) - 2, 0))] or [token]
        postings = [self.trigrams.get(g, set()) for g in grams]
        if not postings or any(not p for p in postings):
            return set()
        return set.intersection(*sorted(postings, key=len))

    def _idf(self, token: str) -> float:
        # SMOOTHED idf. The naive log(n/(1+df)) goes NEGATIVE whenever df >= n
        # (trivially true on a small corpus), which flips the coverage ratio and
        # makes a partial match score 1.0. log((1+n)/(1+df)) + 1 is >= 1 always.
        return math.log((1 + self.n_docs) / (1 + self.doc_freq.get(token, 0))) + 1.0

    def coverage(self, folded_keyword: str, script: str) -> tuple[int, float]:
        """(hits at or above IDF_COVERAGE_KEEP, best idf-coverage seen).

        idf-coverage = the idf mass of the keyword's tokens present in a single
        headline, maximised over headlines. Substring tests, so morphology and
        agglutination are tolerated.
        """
        tokens = keyword_tokens(folded_keyword, script)
        if not tokens:
            return 0, 0.0
        total_idf = sum(self._idf(t) for t in tokens) or 1.0
        candidates: set[int] = set()
        for t in tokens:
            candidates |= self._candidates(t)
        best, hits = 0.0, 0
        for i in candidates:
            fh = self.folded[i]
            got = sum(self._idf(t) for t in tokens if t in fh)
            cov = got / total_idf
            best = max(best, cov)
            if cov >= IDF_COVERAGE_KEEP:
                hits += 1
        return hits, round(best, 4)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest tests/test_attention_match.py -v`
Expected: PASS — 9 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/attention_match.py backend/tests/test_attention_match.py
git commit -m "feat(attention): pure text-matching layer with entity/index/conjunction fixes"
```

---

## Task 2: Pure divergence + tray logic

**Files:**
- Create: `backend/app/services/attention_divergence.py`
- Test: `backend/tests/test_attention_divergence.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_attention_divergence.py
"""Divergence = attention_share − coverage_share per (parent_domain, country).

Never a claim that the press is silent; a ratio between two fields Atlas
measures. Nothing is ever dropped — filtered items carry a reason code.
"""
from app.services.attention_divergence import (
    DOMAIN_MARGIN_TAU, classify_rule_noise, domain_shares, divergence_table,
    tray_reason,
)


def test_domain_shares_sum_to_one():
    shares = domain_shares({"climate-disaster": 30, "economic-stress": 10})
    assert shares == {"climate-disaster": 0.75, "economic-stress": 0.25}


def test_domain_shares_empty_is_empty_not_error():
    assert domain_shares({}) == {}


def test_divergence_is_attention_minus_coverage():
    rows = divergence_table(
        attention={"climate-disaster": 30, "economic-stress": 10},
        coverage={"climate-disaster": 10, "economic-stress": 30},
        coverage_baseline={"climate-disaster": 5, "economic-stress": 5},
    )
    by_domain = {r["domain"]: r for r in rows}
    assert by_domain["climate-disaster"]["divergence"] == 0.5
    assert by_domain["economic-stress"]["divergence"] == -0.5


def test_is_new_requires_zero_coverage_in_the_trailing_baseline():
    rows = divergence_table(
        attention={"public-health": 10},
        coverage={},
        coverage_baseline={},          # absent from this country's history
    )
    assert rows[0]["is_new"] is True

    rows = divergence_table(
        attention={"public-health": 10},
        coverage={},
        coverage_baseline={"public-health": 3},   # covered before, not now
    )
    assert rows[0]["is_new"] is False


def test_classify_rule_noise_catches_the_three_unambiguous_classes():
    assert classify_rule_noise("nottm forest vs blackburn rovers") == "sport_fixture"
    assert classify_rule_noise("loteria del tolima") == "lottery"
    assert classify_rule_noise("clima para amanha") == "routine_weather"
    # A hazard lookup is NOT routine weather — it is the signal.
    assert classify_rule_noise("gempa hari ini") is None
    assert classify_rule_noise("inundaciones en nogales") is None


def test_tray_reason_explains_every_filtered_item_and_keeps_none_silent():
    assert tray_reason({"domain_margin": 0.9, "folded": "loteria nacional"}) == "lottery"
    assert tray_reason({"domain_margin": 0.01, "folded": "some topic"}) == "below_margin"
    assert tray_reason({"domain_margin": DOMAIN_MARGIN_TAU, "folded": "some topic"}) is None


def test_tray_reason_is_total_no_item_can_vanish():
    # Every item either surfaces (None) or carries a reason. There is no third
    # outcome — the no-silent-filtering rail, enforced by construction.
    for item in ({"domain_margin": -1.0, "folded": "x"},
                 {"domain_margin": 1.0, "folded": "real crisis topic"}):
        reason = tray_reason(item)
        assert reason is None or isinstance(reason, str)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_attention_divergence.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.attention_divergence'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/services/attention_divergence.py
"""Attention↔coverage divergence — pure decision layer (no DB, no network).

WHAT IT CLAIMS. Public attention and Atlas coverage are out of proportion for a
(parent_domain, country) pair. That is a statement about Atlas's own corpus and
is provable. It is NOT a claim that the press is silent — measured 2026-07-22,
5 of 5 externally checked "uncovered" candidates were in fact heavily covered by
outlets Atlas does not ingest.

WHY parent_domain AND NOT slug. Whitened-e5 typing separates crisis from noise
reliably, but the SPECIFIC category is often wrong ('snelheidscontrole' →
gang-control). The domain is stable; the slug is not. Only the domain is served.

RELATION TO ECLIPSE. attention_eclipse measures concentration INSIDE coverage
(one story taking >=20% of the room). This measures coverage AGAINST an
independent field. Same shared story-state, a third reading.
"""
from __future__ import annotations

import re

#: Whitened-e5 crisis-minus-noise margin. Measured 2026-07-22: tau=0.06 yields
#: 159 candidates across 60 countries, median 2/country/day. Re-measure after
#: the GDELT entity fix (see the spec's re-measure gate table).
DOMAIN_MARGIN_TAU = 0.06

# The three unambiguous noise classes. Rules are a cheap PRE-FILTER only: a
# hand-built multilingual rule filter measured 93.9% precision at 7-14% recall
# and overfit badly (dev 74.3% -> held-out 7.1%), so rules never gate — the
# whitened-e5 margin does.
_SPORT_FIXTURE = re.compile(r"\b(vs|v|x)\b|\bfc\b|\bmatch\b|\bfixture\b")
_LOTTERY = re.compile(
    r"loteri|lotto|jackpot|euromillion|eurojackpot|resultado[s]? del sorteo|"
    r"chontico|quiniela|\bhuay\b|\bbet\b"
)
_ROUTINE_WEATHER = re.compile(
    r"\b(clima|tempo|weather|meteo|m[eé]t[eé]o|wetter|pogoda|vremea|hava durumu)\b"
    r".*\b(amanha|amanhã|manana|mañana|tomorrow|demain|morgen|utre|maine|yarin)\b"
    r"|previsao do tempo|prevision del tiempo|weather forecast"
)
# Hazard lookups LOOK like weather but ARE the signal — never trayed as weather.
_HAZARD = re.compile(
    r"gempa|sismo|terremoto|temblor|earthquake|quake|huracan|hurac[aá]n|"
    r"hurricane|ciclon|cyclone|tifon|typhoon|inundacion|inundaç|flood|banjir|"
    r"landslide|deslizamiento|wildfire|incendio|tsunami|volcan|eruption|"
    r"nivel do|storm surge"
)


def classify_rule_noise(folded_keyword: str) -> str | None:
    """One of 'sport_fixture' | 'lottery' | 'routine_weather', else None.

    Hazard wins over weather by construction: an earthquake or flood lookup is
    a risk signal, not a forecast check.
    """
    text = folded_keyword or ""
    if _HAZARD.search(text):
        return None
    if _LOTTERY.search(text):
        return "lottery"
    if _ROUTINE_WEATHER.search(text):
        return "routine_weather"
    if _SPORT_FIXTURE.search(text):
        return "sport_fixture"
    return None


def tray_reason(item: dict) -> str | None:
    """Why this item is trayed instead of surfaced, or None if it surfaces.

    TOTAL by construction — every item gets either None or a reason string.
    Nothing is ever silently discarded (the standing no-silent-filtering rail).
    """
    rule = classify_rule_noise(item.get("folded", ""))
    if rule:
        return rule
    if float(item.get("domain_margin", 0.0)) < DOMAIN_MARGIN_TAU:
        return "below_margin"
    return None


def domain_shares(volume_by_domain: dict[str, float]) -> dict[str, float]:
    """Each domain's share of the total. Empty input -> empty output."""
    total = sum(v for v in volume_by_domain.values() if v > 0)
    if total <= 0:
        return {}
    return {d: v / total for d, v in volume_by_domain.items() if v > 0}


def divergence_table(
    *,
    attention: dict[str, float],
    coverage: dict[str, float],
    coverage_baseline: dict[str, float],
) -> list[dict]:
    """One row per domain present in attention or coverage.

    `coverage_baseline` is the trailing 7-day coverage for the same country; a
    domain absent from it AND uncovered now is NEW, not merely under-covered.
    """
    a_share = domain_shares(attention)
    c_share = domain_shares(coverage)
    rows = []
    for domain in sorted(set(a_share) | set(c_share)):
        att = a_share.get(domain, 0.0)
        cov = c_share.get(domain, 0.0)
        rows.append({
            "domain": domain,
            "attention_share": round(att, 4),
            "coverage_share": round(cov, 4),
            "divergence": round(att - cov, 4),
            "under_the_radar": att > cov,
            "is_new": att > 0 and coverage.get(domain, 0) == 0
                      and coverage_baseline.get(domain, 0) == 0,
        })
    return sorted(rows, key=lambda r: -r["divergence"])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest tests/test_attention_divergence.py -v`
Expected: PASS — 7 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/attention_divergence.py backend/tests/test_attention_divergence.py
git commit -m "feat(attention): pure divergence + tray logic, domain-level by design"
```

---

## Task 3: Anchor set

**Files:**
- Create: `backend/app/services/attention_anchors.py`
- Test: `backend/tests/test_attention_anchors.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_attention_anchors.py
from app.services.attention_anchors import NEGATIVE_ANCHORS, build_anchor_set


def test_build_anchor_set_appends_negative_anchors_after_crisis_anchors():
    seeds = [
        {"slug": "flood-landslide-disaster", "label": "Flood and landslide disaster",
         "description": "Floods, landslides, evacuations.",
         "parent_domain": "climate-disaster"},
    ]
    keys, texts, n_crisis, domains = build_anchor_set(seeds)
    assert n_crisis == 1
    assert keys[0] == "flood-landslide-disaster"
    assert keys[1:] == list(NEGATIVE_ANCHORS)
    assert len(keys) == len(texts)
    assert texts[0] == "Flood and landslide disaster. Floods, landslides, evacuations."
    assert domains["flood-landslide-disaster"] == "climate-disaster"


def test_negative_anchors_cover_every_measured_noise_class():
    # Base rates measured 2026-07-22 (n=280): sport 25.7%, commercial 14.3%,
    # entertainment 13.2%, bare person 10.4%, routine weather 5.4%, lottery 0.7%.
    for expected in ("_noise_sport_fixture", "_noise_lottery", "_noise_entertainment",
                     "_noise_routine_weather", "_noise_commercial",
                     "_noise_person_only", "_noise_video_game"):
        assert expected in NEGATIVE_ANCHORS


def test_build_anchor_set_tolerates_missing_description():
    seeds = [{"slug": "s", "label": "L", "description": None, "parent_domain": "d"}]
    _keys, texts, _n, _domains = build_anchor_set(seeds)
    assert texts[0] == "L."
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_attention_anchors.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.attention_anchors'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/services/attention_anchors.py
"""Anchors for typing a public-attention query into Atlas's taxonomy.

Crisis anchors are built from the 30 seed `atlas_topics` rows (label +
description). Negative anchors name the noise classes MEASURED in the attention
stream on 2026-07-22 (n=280 hand labels) so the argmax has somewhere honest to
land instead of forcing every lookup into a crisis category.
"""
from __future__ import annotations

NEGATIVE_ANCHORS: dict[str, str] = {
    "_noise_sport_fixture":
        "a football or sports fixture between two teams, match result, league "
        "table, kickoff time, player transfer or squad news",
    "_noise_lottery":
        "lottery draw results, jackpot numbers, betting odds, prize draw, "
        "gambling results",
    "_noise_entertainment":
        "a television series, film, music album, celebrity gossip, reality "
        "show, streaming release or awards ceremony",
    "_noise_routine_weather":
        "the ordinary weather forecast for tomorrow, temperature today, "
        "whether it will rain, local forecast",
    "_noise_commercial":
        "a shop, bank, ticket seller, mobile operator, student portal, product "
        "price, promotion, customer login or how to buy something",
    "_noise_person_only":
        "the biography of a well known person, an actor, singer, athlete or "
        "influencer",
    "_noise_video_game":
        "a video game, game release date, console, in-game item or character",
}


def build_anchor_set(
    seed_topics: list[dict],
) -> tuple[list[str], list[str], int, dict[str, str]]:
    """(anchor_keys, anchor_texts, n_crisis_anchors, slug -> parent_domain).

    Crisis anchors come first so `argmax < n_crisis` means "typed as a crisis
    domain" and anything at or beyond it is a named noise class.
    """
    keys = [t["slug"] for t in seed_topics]
    texts = [f"{t['label']}. {(t.get('description') or '').strip()}".strip()
             for t in seed_topics]
    domains = {t["slug"]: t.get("parent_domain") or "" for t in seed_topics}
    return (keys + list(NEGATIVE_ANCHORS),
            texts + list(NEGATIVE_ANCHORS.values()),
            len(seed_topics),
            domains)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest tests/test_attention_anchors.py -v`
Expected: PASS — 3 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/attention_anchors.py backend/tests/test_attention_anchors.py
git commit -m "feat(attention): crisis + measured-noise anchor set"
```

---

## Task 4: Migration 090

**Files:**
- Create: `backend/migrations/090_public_attention_typed.sql`

- [ ] **Step 1: Write the migration**

```sql
-- backend/migrations/090_public_attention_typed.sql
-- Precomputed public-attention typing + coverage match.
--
-- The API box has no torch, and typing ~7,000 trend keywords per 24h cannot
-- happen per request. The M1 job (scripts/type_public_attention.py) embeds,
-- whitens, types and matches the corpus, then upserts one row per
-- (country_code, keyword, day). Serving is a pure read plus share arithmetic.
--
-- Reversible: DROP TABLE public_attention_typed;

CREATE TABLE IF NOT EXISTS public_attention_typed (
    id              BIGSERIAL PRIMARY KEY,
    day             DATE        NOT NULL,
    country_code    CHAR(2)     NOT NULL,
    keyword         TEXT        NOT NULL,
    folded          TEXT        NOT NULL,
    script          TEXT        NOT NULL,
    attention_volume INTEGER    NOT NULL DEFAULT 0,
    attention_rank  INTEGER,
    -- typing (whitened multilingual-e5 argmax over crisis ∪ noise anchors)
    slug            TEXT,          -- closest crisis category (hint only, often wrong)
    domain          TEXT,          -- parent_domain — the served granularity
    domain_margin   REAL,          -- crisis-best minus noise-best, whitened cosine
    noise_class     TEXT,          -- winning negative anchor when noise wins
    -- coverage, measured with app/services/attention_match.IdfIndex
    coverage_count  INTEGER     NOT NULL DEFAULT 0,
    coverage_best   REAL        NOT NULL DEFAULT 0,
    coverage_samples JSONB      NOT NULL DEFAULT '[]'::jsonb,
    -- provenance
    model_version   TEXT        NOT NULL,
    computed_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (day, country_code, keyword)
);

CREATE INDEX IF NOT EXISTS idx_pat_day_country
    ON public_attention_typed (day DESC, country_code);
CREATE INDEX IF NOT EXISTS idx_pat_domain
    ON public_attention_typed (day DESC, domain)
    WHERE domain IS NOT NULL;

-- Server-only, same posture as migration 082: no Supabase default grants.
ALTER TABLE public_attention_typed ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public_attention_typed FROM anon, authenticated;
REVOKE ALL ON SEQUENCE public_attention_typed_id_seq FROM anon, authenticated;
```

- [ ] **Step 2: Verify the SQL parses without applying it**

Run: `cd backend && .venv/bin/python -c "import pathlib; s=pathlib.Path('migrations/090_public_attention_typed.sql').read_text(); assert 'CREATE TABLE IF NOT EXISTS public_attention_typed' in s and 'REVOKE ALL' in s; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Apply to prod via the Supabase SQL editor / MCP `apply_migration`**

Expected: table `public_attention_typed` exists, 0 rows.

- [ ] **Step 4: Commit**

```bash
git add backend/migrations/090_public_attention_typed.sql
git commit -m "feat(attention): migration 090 public_attention_typed"
```

---

## Task 5: The M1 typing + coverage job

**Files:**
- Create: `backend/scripts/type_public_attention.py`
- Test: `backend/tests/test_type_public_attention.py`

- [ ] **Step 1: Write the failing test**

The DB and the model are not unit-testable; the row-building step is, so that
is what the test pins.

```python
# backend/tests/test_type_public_attention.py
import numpy as np

from scripts.type_public_attention import build_rows, type_queries


def test_type_queries_picks_crisis_when_crisis_anchor_is_nearer():
    # 2 crisis anchors, 1 noise anchor, in a toy 3-dim space.
    anchors = np.array([[1.0, 0, 0], [0, 1.0, 0], [0, 0, 1.0]], dtype=np.float32)
    queries = np.array([[0.9, 0.1, 0.0]], dtype=np.float32)
    typed = type_queries(queries, anchors, n_crisis=2,
                         keys=["a-slug", "b-slug", "_noise_x"])
    assert typed[0]["slug"] == "a-slug"
    assert typed[0]["domain_margin"] > 0
    assert typed[0]["noise_class"] is None


def test_type_queries_names_the_noise_class_when_noise_wins():
    anchors = np.array([[1.0, 0, 0], [0, 0, 1.0]], dtype=np.float32)
    queries = np.array([[0.0, 0.0, 1.0]], dtype=np.float32)
    typed = type_queries(queries, anchors, n_crisis=1, keys=["a-slug", "_noise_x"])
    assert typed[0]["noise_class"] == "_noise_x"
    assert typed[0]["domain_margin"] < 0


def test_build_rows_joins_typing_coverage_and_provenance():
    trends = [{"country_code": "MX", "keyword": "inundaciones en nogales",
               "vol": 1000, "rank": 3}]
    typed = [{"slug": "flood-landslide-disaster", "domain_margin": 0.16,
              "noise_class": None}]
    coverage = [(0, 0.2, [])]
    rows = build_rows(trends, typed, coverage,
                      domains={"flood-landslide-disaster": "climate-disaster"},
                      day="2026-07-22", model_version="e5-whitened-v1")
    assert len(rows) == 1
    row = rows[0]
    assert row["country_code"] == "MX"
    assert row["folded"] == "inundaciones en nogales"
    assert row["script"] == "LATIN"
    assert row["domain"] == "climate-disaster"
    assert row["coverage_count"] == 0
    assert row["model_version"] == "e5-whitened-v1"


def test_build_rows_leaves_domain_null_when_noise_wins():
    trends = [{"country_code": "CO", "keyword": "loteria del tolima",
               "vol": 5000, "rank": 2}]
    typed = [{"slug": None, "domain_margin": -0.2, "noise_class": "_noise_lottery"}]
    rows = build_rows(trends, typed, [(0, 0.0, [])], domains={},
                      day="2026-07-22", model_version="e5-whitened-v1")
    assert rows[0]["domain"] is None
    assert rows[0]["noise_class"] == "_noise_lottery"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_type_public_attention.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.type_public_attention'`

- [ ] **Step 3: Write minimal implementation**

```python
#!/usr/bin/env python3
"""Type public attention (trends_v2) into Atlas's taxonomy and match coverage.

Runs on the M1 (mlvenv has torch; the Fly API box does not) and writes
public_attention_typed. Read-only on trends_v2 / signals_v2 / atlas_topics.

WHY WHITENING. Raw multilingual-e5 is anisotropic: on 400 real trend keywords
the crisis-minus-noise margin maxed at +0.052 with a p99-p1 similarity spread of
0.122. Applying Atlas's ONE global all-but-the-top transform moved that to
+0.206 and 0.308 — a 2.5-4x decompression that gives a threshold somewhere to
live. Measured 2026-07-22.

Usage:
  mlvenv/bin/python -m scripts.type_public_attention --hours 24 [--dry-run]
"""
from __future__ import annotations

import argparse
import asyncio
import os
from datetime import datetime, timezone

import asyncpg
import numpy as np

from app.services.attention_anchors import build_anchor_set
from app.services.attention_match import IdfIndex, script_of, unescape_fold
from app.services.whitening import apply_whitening, load_whitening

MODEL = "intfloat/multilingual-e5-base"
MODEL_VERSION = "attention-typing-e5-whitened-v1"
COVERAGE_SAMPLE_CAP = 3


def type_queries(queries: np.ndarray, anchors: np.ndarray, *, n_crisis: int,
                 keys: list[str]) -> list[dict]:
    """argmax over crisis ∪ noise anchors. Returns slug / margin / noise_class.

    margin = best crisis similarity − best noise similarity. Positive means the
    query is nearer a crisis anchor than to any named noise class.
    """
    sims = queries @ anchors.T
    out = []
    for row in sims:
        best_crisis = int(np.argmax(row[:n_crisis]))
        best_noise = int(np.argmax(row[n_crisis:])) + n_crisis
        margin = float(row[best_crisis] - row[best_noise])
        noise_wins = margin < 0
        out.append({
            "slug": None if noise_wins else keys[best_crisis],
            "domain_margin": round(margin, 4),
            "noise_class": keys[best_noise] if noise_wins else None,
        })
    return out


def build_rows(trends: list[dict], typed: list[dict],
               coverage: list[tuple[int, float, list]], *,
               domains: dict[str, str], day: str,
               model_version: str) -> list[dict]:
    """Join the three parallel lists into upsertable rows."""
    rows = []
    for t, ty, (count, best, samples) in zip(trends, typed, coverage):
        folded = unescape_fold(t["keyword"])
        rows.append({
            "day": day,
            "country_code": t["country_code"],
            "keyword": t["keyword"],
            "folded": folded,
            "script": script_of(folded),
            "attention_volume": int(t.get("vol") or 0),
            "attention_rank": t.get("rank"),
            "slug": ty["slug"],
            "domain": domains.get(ty["slug"]) if ty["slug"] else None,
            "domain_margin": ty["domain_margin"],
            "noise_class": ty["noise_class"],
            "coverage_count": count,
            "coverage_best": best,
            "coverage_samples": samples,
            "model_version": model_version,
        })
    return rows


def _embed(texts: list[str], prefix: str) -> np.ndarray:
    import torch
    from transformers import AutoModel, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(MODEL)
    model = AutoModel.from_pretrained(MODEL).eval()
    out = []
    with torch.no_grad():
        for i in range(0, len(texts), 32):
            enc = tok([f"{prefix}: {t}" for t in texts[i:i + 32]], padding=True,
                      truncation=True, max_length=96, return_tensors="pt")
            h = model(**enc).last_hidden_state
            mask = enc["attention_mask"].unsqueeze(-1).float()
            emb = (h * mask).sum(1) / mask.sum(1)
            out.append(torch.nn.functional.normalize(emb, dim=-1).numpy())
    return np.vstack(out)


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=24)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    conn = await asyncpg.connect(os.environ["DATABASE_URL"], statement_cache_size=0)
    await conn.execute("SET statement_timeout='180s'")
    trend_rows = await conn.fetch(
        f"""SELECT country_code, keyword, MAX(approximate_volume) AS vol,
                   MIN(rank) AS rank
            FROM trends_v2
            WHERE hour_bucket > NOW() - INTERVAL '{int(args.hours)} hours'
            GROUP BY country_code, keyword""")
    press_rows = await conn.fetch(
        f"""SELECT headline FROM signals_v2
            WHERE timestamp > NOW() - INTERVAL '{int(args.hours) * 2} hours'
              AND source_family IS DISTINCT FROM 'social'
              AND headline IS NOT NULL AND headline <> ''""")
    seed_rows = await conn.fetch(
        """SELECT slug, label, description, parent_domain FROM atlas_topics
           WHERE is_active AND origin = 'seed' ORDER BY slug""")

    trends = [dict(r) for r in trend_rows]
    keys, texts, n_crisis, domains = build_anchor_set([dict(r) for r in seed_rows])

    whitening = load_whitening()
    anchors = apply_whitening(_embed(texts, "passage"), whitening)
    queries = apply_whitening(_embed([t["keyword"] for t in trends], "query"), whitening)
    typed = type_queries(queries, anchors, n_crisis=n_crisis, keys=keys)

    index = IdfIndex([r["headline"] for r in press_rows])
    coverage = []
    for t in trends:
        folded = unescape_fold(t["keyword"])
        count, best = index.coverage(folded, script_of(folded))
        coverage.append((count, best, []))

    day = datetime.now(timezone.utc).date().isoformat()
    rows = build_rows(trends, typed, coverage, domains=domains, day=day,
                      model_version=MODEL_VERSION)

    print(f"typed {len(rows)} attention rows across "
          f"{len({r['country_code'] for r in rows})} countries; "
          f"crisis-typed {sum(1 for r in rows if r['domain'])}")
    if args.dry_run:
        await conn.close()
        return

    await conn.executemany(
        """INSERT INTO public_attention_typed
             (day, country_code, keyword, folded, script, attention_volume,
              attention_rank, slug, domain, domain_margin, noise_class,
              coverage_count, coverage_best, coverage_samples, model_version)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14::jsonb,$15)
           ON CONFLICT (day, country_code, keyword) DO UPDATE SET
             attention_volume = EXCLUDED.attention_volume,
             attention_rank   = EXCLUDED.attention_rank,
             slug = EXCLUDED.slug, domain = EXCLUDED.domain,
             domain_margin = EXCLUDED.domain_margin,
             noise_class = EXCLUDED.noise_class,
             coverage_count = EXCLUDED.coverage_count,
             coverage_best = EXCLUDED.coverage_best,
             model_version = EXCLUDED.model_version,
             computed_at = NOW()""",
        [(r["day"], r["country_code"], r["keyword"], r["folded"], r["script"],
          r["attention_volume"], r["attention_rank"], r["slug"], r["domain"],
          r["domain_margin"], r["noise_class"], r["coverage_count"],
          r["coverage_best"], "[]", r["model_version"]) for r in rows])
    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest tests/test_type_public_attention.py -v`
Expected: PASS — 4 passed

- [ ] **Step 5: Dry-run against prod on the M1**

Run: `cd backend && /Users/pedro/AtlasLocalWorker/mlvenv/bin/python -m scripts.type_public_attention --hours 24 --dry-run`
Expected: a line like `typed 6900 attention rows across 99 countries; crisis-typed ~1900`

- [ ] **Step 6: Commit**

```bash
git add backend/scripts/type_public_attention.py backend/tests/test_type_public_attention.py
git commit -m "feat(attention): M1 typing + coverage job writing public_attention_typed"
```

---

## Task 6: The divergence endpoint

**Files:**
- Modify: `backend/app/routers/attention_threads.py`
- Test: `backend/tests/test_attention_divergence_endpoint.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_attention_divergence_endpoint.py
"""Contract freeze for attention-coverage-divergence-v1."""
from app.routers.attention_threads import (
    CONTRACT_DIVERGENCE, build_divergence_payload,
)


def _row(keyword, domain, margin, coverage, volume=1000, noise=None):
    return {"keyword": keyword, "folded": keyword, "country_code": "MX",
            "script": "LATIN", "attention_volume": volume, "attention_rank": 3,
            "slug": "flood-landslide-disaster", "domain": domain,
            "domain_margin": margin, "noise_class": noise,
            "coverage_count": coverage, "coverage_best": 0.2,
            "coverage_samples": []}


def test_payload_carries_the_contract_and_a_verify_url():
    payload = build_divergence_payload(
        [_row("inundaciones en nogales", "climate-disaster", 0.16, 0)],
        coverage_by_domain={"economic-stress": 40},
        coverage_baseline={}, country="MX", hours=24, limit=15)
    assert payload["contract"] == CONTRACT_DIVERGENCE
    item = payload["items"][0]
    assert item["verify_url"].startswith("https://")
    assert "inundaciones" in item["verify_url"]


def test_payload_never_asserts_press_silence():
    payload = build_divergence_payload(
        [_row("inundaciones en nogales", "climate-disaster", 0.16, 0)],
        coverage_by_domain={}, coverage_baseline={}, country="MX",
        hours=24, limit=15)
    blob = repr(payload).lower()
    for forbidden in ("silent", "not covered by the press", "press is silent",
                      "uncovered by media"):
        assert forbidden not in blob


def test_trayed_items_are_present_with_a_reason_never_dropped():
    payload = build_divergence_payload(
        [_row("loteria del tolima", None, -0.2, 0, noise="_noise_lottery"),
         _row("inundaciones en nogales", "climate-disaster", 0.16, 0)],
        coverage_by_domain={}, coverage_baseline={}, country="MX",
        hours=24, limit=15)
    assert len(payload["items"]) == 1
    assert len(payload["tray"]) == 1
    assert payload["tray"][0]["reason_code"] == "lottery"
    assert len(payload["items"]) + len(payload["tray"]) == 2


def test_payload_exposes_the_domain_share_tables():
    payload = build_divergence_payload(
        [_row("inundaciones en nogales", "climate-disaster", 0.16, 0)],
        coverage_by_domain={"economic-stress": 40}, coverage_baseline={},
        country="MX", hours=24, limit=15)
    assert payload["attention_share_by_domain"]["climate-disaster"] == 1.0
    assert payload["coverage_share_by_domain"]["economic-stress"] == 1.0
    assert payload["divergence_by_domain"][0]["domain"] == "climate-disaster"


def test_press_supply_is_context_and_never_gates_an_item_out():
    # The retired _INFO_DESERT_FLOOR gated on supply and was measured INVERTED.
    # Supply must be reported on the item and change nothing about surfacing.
    row = _row("inundaciones en nogales", "climate-disaster", 0.16, 0)
    with_supply = build_divergence_payload(
        [row], coverage_by_domain={}, coverage_baseline={}, country="MX",
        hours=24, limit=15, press_supply_by_cc={"MX": 3})
    without = build_divergence_payload(
        [row], coverage_by_domain={}, coverage_baseline={}, country="MX",
        hours=24, limit=15, press_supply_by_cc={"MX": 90000})
    assert with_supply["items"][0]["press_supply"] == 3
    assert without["items"][0]["press_supply"] == 90000
    assert len(with_supply["items"]) == len(without["items"]) == 1


def test_empty_input_returns_honest_empty_not_an_error():
    payload = build_divergence_payload([], coverage_by_domain={},
                                       coverage_baseline={}, country="MX",
                                       hours=24, limit=15)
    assert payload["items"] == []
    assert payload["tray"] == []
    assert payload["notes"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_attention_divergence_endpoint.py -v`
Expected: FAIL — `ImportError: cannot import name 'CONTRACT_DIVERGENCE'`

- [ ] **Step 3: Add the payload builder and route to `attention_threads.py`**

Append to `backend/app/routers/attention_threads.py`:

```python
import urllib.parse as _urlparse
from collections import defaultdict

from app.services.attention_divergence import divergence_table, tray_reason

CONTRACT_DIVERGENCE = "attention-coverage-divergence-v1"


def _verify_url(keyword: str) -> str:
    """External escape hatch. Atlas reports only its own corpus; the analyst
    checks the world. Measured 2026-07-22: 5 of 5 'uncovered' candidates were
    in fact covered by outlets Atlas does not ingest."""
    return "https://duckduckgo.com/?q=" + _urlparse.quote(keyword)


def build_divergence_payload(rows: list[dict], *, coverage_by_domain: dict,
                             coverage_baseline: dict, country: str | None,
                             hours: int, limit: int,
                             press_supply_by_cc: dict | None = None) -> dict:
    """Pure payload assembly — no DB. Every input row lands in items or tray.

    `press_supply_by_cc` is CONTEXT on an item, never a gate. The old
    _INFO_DESERT_FLOOR gated on it and was measured inverted (silence RISES with
    press volume), so supply is reported and never thresholded.
    """
    press_supply_by_cc = press_supply_by_cc or {}
    attention_by_domain: dict[str, float] = defaultdict(float)
    for r in rows:
        if r.get("domain"):
            attention_by_domain[r["domain"]] += max(int(r.get("attention_volume") or 0), 1)

    div_rows = divergence_table(attention=dict(attention_by_domain),
                                coverage=coverage_by_domain,
                                coverage_baseline=coverage_baseline)
    div_by_domain = {d["domain"]: d for d in div_rows}

    items, tray = [], []
    for r in rows:
        reason = tray_reason(r)
        base = {
            "query": r["keyword"],
            "country_code": r["country_code"],
            "script": r["script"],
            "attention_volume": r["attention_volume"],
            "attention_rank": r["attention_rank"],
            "domain": r.get("domain"),
            "domain_margin": r.get("domain_margin"),
            "noise_class": r.get("noise_class"),
            "coverage_count": r.get("coverage_count", 0),
            "coverage_samples": r.get("coverage_samples") or [],
            "press_supply": press_supply_by_cc.get(r["country_code"], 0),
            "verify_url": _verify_url(r["keyword"]),
        }
        if reason:
            tray.append({**base, "reason_code": reason})
            continue
        d = div_by_domain.get(r.get("domain") or "", {})
        items.append({**base,
                      "divergence": d.get("divergence", 0.0),
                      "is_new": d.get("is_new", False),
                      "reason_codes": ["typed_crisis_domain",
                                       "attention_above_coverage"
                                       if d.get("under_the_radar") else
                                       "attention_below_coverage"]})

    items.sort(key=lambda x: (-(x["divergence"] or 0), -(x["attention_volume"] or 0)))
    notes = []
    if not rows:
        notes.append("no typed public attention in this window")
    notes.append("divergence compares attention and coverage INSIDE Atlas's "
                 "corpus; it is not a claim about what the press published")
    return {
        "contract": CONTRACT_DIVERGENCE,
        "country": country, "hours": hours,
        "attention_share_by_domain": {d["domain"]: d["attention_share"] for d in div_rows},
        "coverage_share_by_domain": {d["domain"]: d["coverage_share"] for d in div_rows},
        "divergence_by_domain": div_rows,
        "items": items[:limit],
        "tray": tray,
        "notes": notes,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/api/v2/attention/divergence")
async def get_attention_divergence(
    country: str | None = Query(None, min_length=2, max_length=2),
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(15, ge=1, le=50),
) -> dict:
    cc = country.upper() if country else None
    if db.pool is None:
        return {"contract": CONTRACT_DIVERGENCE, "items": [], "tray": [],
                "notes": ["database unavailable"]}
    async with db.pool.acquire() as conn:
        await conn.execute("SET statement_timeout = 12000")
        rows = [dict(r) for r in await conn.fetch(
            """SELECT keyword, folded, country_code, script, attention_volume,
                      attention_rank, slug, domain, domain_margin, noise_class,
                      coverage_count, coverage_best, coverage_samples
               FROM public_attention_typed
               WHERE day >= (CURRENT_DATE - 1)
                 AND ($1::text IS NULL OR country_code = $1)
               ORDER BY domain_margin DESC NULLS LAST
               LIMIT 400""", cc)]
        cov = {r["parent_domain"]: r["n"] for r in await conn.fetch(
            f"""SELECT t.parent_domain, COUNT(*)::int AS n
                FROM signal_topic_assignments a
                JOIN atlas_topics t ON t.id = a.topic_id
                JOIN signals_v2 s ON s.id = a.signal_id
                WHERE a.assigned_at > NOW() - ($1::int * INTERVAL '1 hour')
                  AND ($2::text IS NULL OR s.country_code = $2)
                  AND t.parent_domain IS NOT NULL
                GROUP BY t.parent_domain""", hours, cc)}
        base = {r["parent_domain"]: r["n"] for r in await conn.fetch(
            """SELECT t.parent_domain, COUNT(*)::int AS n
               FROM signal_topic_assignments a
               JOIN atlas_topics t ON t.id = a.topic_id
               JOIN signals_v2 s ON s.id = a.signal_id
               WHERE a.assigned_at > NOW() - INTERVAL '7 days'
                 AND ($1::text IS NULL OR s.country_code = $1)
                 AND t.parent_domain IS NOT NULL
               GROUP BY t.parent_domain""", cc)}
        supply = {r["country_code"]: r["n"] for r in await conn.fetch(
            f"""SELECT country_code, COUNT(*)::int AS n
                FROM signals_v2
                WHERE timestamp > NOW() - ($1::int * INTERVAL '1 hour')
                  AND source_family IS DISTINCT FROM 'social'
                  AND ($2::text IS NULL OR country_code = $2)
                GROUP BY country_code""", hours, cc)}
    return build_divergence_payload(rows, coverage_by_domain=cov,
                                    coverage_baseline=base, country=cc,
                                    hours=hours, limit=limit,
                                    press_supply_by_cc=supply)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest tests/test_attention_divergence_endpoint.py -v`
Expected: PASS — 5 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/attention_threads.py backend/tests/test_attention_divergence_endpoint.py
git commit -m "feat(attention): GET /api/v2/attention/divergence, contract v1"
```

---

## Task 7: Delete `_INFO_DESERT_FLOOR` and retire the silent-risk endpoint

**Files:**
- Modify: `backend/app/routers/attention_threads.py`
- Delete: `backend/app/services/silent_risk.py`

- [ ] **Step 1: Confirm nothing consumes the old endpoint**

Run: `grep -rn "silent-risks\|silent_risk" backend/app frontend-v2/src scripts | grep -v attention_threads.py`
Expected: no output (measured 2026-07-22: backend-only, zero frontend consumers)

- [ ] **Step 2: Remove the old route, helpers and imports**

Delete from `attention_threads.py`: the `get_silent_risks` route, `_forum_topics`,
`_lexical_coverage`, `_distinctive_token`, `_fetch_wiki_categories`, `_ckey`,
`_NEWS_SUBREDDITS`, `_MEDIA_FLOOR`, `_INFO_DESERT_FLOOR`, `_MAX_TOPICS`,
`_STOPWORDS`, and the `from app.services.silent_risk import ...` block.

Rationale to put in the module docstring:

```python
"""Public-attention lenses.

GET /api/v2/attention/divergence — attention vs coverage share per domain.

The former /api/v2/attention/silent-risks is retired. Measured 2026-07-22:
(a) press silence is unverifiable from Atlas's corpus — 5 of 5 externally
checked "uncovered" candidates were heavily covered by outlets Atlas does not
ingest; (b) _INFO_DESERT_FLOOR = 40 signals/window was miscalibrated AND
inverted — it labelled 74 of 220 countries a desert and 0 of the 99 countries
that actually have trends attention, while silence RISES with press volume
(17.9% silent at 0-50 press vs 33.6% at 800-1600). It is deleted, not retuned.
"""
```

- [ ] **Step 3: Delete the superseded module**

```bash
git rm backend/app/services/silent_risk.py
```

- [ ] **Step 4: Run the full attention suite**

Run: `cd backend && .venv/bin/python -m pytest tests/test_attention_match.py tests/test_attention_divergence.py tests/test_attention_anchors.py tests/test_attention_divergence_endpoint.py tests/test_attention_eclipse.py -v`
Expected: PASS — all green, no import errors

- [ ] **Step 5: Commit**

```bash
git add -A backend/app/routers/attention_threads.py backend/app/services/silent_risk.py
git commit -m "refactor(attention): retire silent-risks, delete inverted info-desert floor"
```

---

## Task 8: Cron wiring

**Files:**
- Modify: `scripts/run-atlas-topic-classifier.sh`

- [ ] **Step 1: Add Step 6 after the existing Step 5b**

```bash
# Step 6 (2026-07-22): type public attention (trends_v2) into the taxonomy and
# match it against the press corpus. Writes public_attention_typed, which
# GET /api/v2/attention/divergence reads. Heavy (e5 + whitening) so it runs
# here on the M1, never on the API box. Best-effort: a failure must never
# abort the classifier chain.
if [ "${ATLAS_ATTENTION_TYPING:-on}" = "on" ]; then
  echo "Step 6: typing public attention"
  "$MLVENV/bin/python" -m scripts.type_public_attention --hours 24 \
    || echo "Step 6 FAILED (non-fatal): attention typing"
fi
```

- [ ] **Step 2: Verify the script still parses**

Run: `bash -n scripts/run-atlas-topic-classifier.sh && echo ok`
Expected: `ok`

- [ ] **Step 3: Sync to the executed copy**

```bash
cp scripts/run-atlas-topic-classifier.sh /Users/pedro/AtlasLocalWorker/run-atlas-topic-classifier.sh
diff scripts/run-atlas-topic-classifier.sh /Users/pedro/AtlasLocalWorker/run-atlas-topic-classifier.sh && echo "byte-identical"
```

Expected: `byte-identical`

- [ ] **Step 4: Commit**

```bash
git add scripts/run-atlas-topic-classifier.sh
git commit -m "chore(cron): Step 6 — public-attention typing on the 30-min cadence"
```

---

## Task 9: Threshold calibration — GATE for the surfaces

**Runs only after the GDELT HTML-entity fix has landed and backfilled.**

**Files:**
- Modify: `backend/app/services/attention_match.py` (`IDF_COVERAGE_KEEP`)
- Modify: `backend/app/services/attention_divergence.py` (`DOMAIN_MARGIN_TAU`)
- Create: `docs/research/silent-risk/2026-XX-XX-post-entity-fix-calibration.md`

- [ ] **Step 1: Re-run the job and record the new distribution**

Run: `cd backend && /Users/pedro/AtlasLocalWorker/mlvenv/bin/python -m scripts.type_public_attention --hours 24 --dry-run`
Record: total rows, crisis-typed count, and the share with `coverage_count = 0`.

- [ ] **Step 2: Sweep the margin and pick a band-sized operating point**

```sql
SELECT width_bucket(domain_margin, -0.3, 0.3, 12) AS bucket,
       MIN(domain_margin)::numeric(5,3) AS lo,
       COUNT(*) AS n,
       COUNT(*) FILTER (WHERE coverage_count = 0) AS uncovered
FROM public_attention_typed
WHERE day = CURRENT_DATE AND domain IS NOT NULL
GROUP BY 1 ORDER BY 1;
```

Target: a τ giving a **median of 2–5 surfaced items per country per day** — the
band size the L1 country door can carry. Pre-fix that was τ = 0.06 → 159
candidates / 60 countries / median 2.

- [ ] **Step 3: Hand-label 60 items at the chosen τ and record precision**

Sample 60 surfaced items across ≥15 countries, label REAL-STORY / HAZARD /
noise. Pre-fix base rate in the unfiltered silent set was 22.5% (n=280); the
filtered tray must beat it substantially or τ is wrong.

- [ ] **Step 4: Write the calibration artifact and update both constants**

The doc records: date, corpus state, τ swept, chosen τ, measured precision with
its CI, and the resulting band size. Update `IDF_COVERAGE_KEEP` and
`DOMAIN_MARGIN_TAU` to the measured values.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/attention_match.py backend/app/services/attention_divergence.py docs/research/silent-risk/
git commit -m "fix(attention): calibrate thresholds on the entity-fixed corpus"
```

---

## Task 10: Frontend pure layer

**Files:**
- Create: `frontend-v2/src/lib/attentionDivergence.ts`
- Test: `frontend-v2/src/lib/attentionDivergence.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
// frontend-v2/src/lib/attentionDivergence.test.ts
import { describe, expect, it } from 'vitest'
import { divergenceLabel, domainLabel, topDivergent } from './attentionDivergence'
import type { DivergenceItem } from './attentionDivergence'

const item = (query: string, divergence: number, volume: number): DivergenceItem => ({
  query, country_code: 'MX', script: 'LATIN', attention_volume: volume,
  attention_rank: 3, domain: 'climate-disaster', domain_margin: 0.16,
  noise_class: null, coverage_count: 0, coverage_samples: [], press_supply: 120,
  verify_url: 'https://duckduckgo.com/?q=x', divergence, is_new: false,
  reason_codes: ['typed_crisis_domain'],
})

describe('attentionDivergence', () => {
  it('ranks by divergence then attention volume', () => {
    const out = topDivergent([item('a', 0.1, 100), item('b', 0.5, 10),
                              item('c', 0.5, 900)], 2)
    expect(out.map(i => i.query)).toEqual(['c', 'b'])
  })

  it('caps the returned list', () => {
    expect(topDivergent([item('a', 0.1, 1), item('b', 0.2, 1)], 1)).toHaveLength(1)
  })

  it('labels the domain as a hedged hint, never an assertion', () => {
    expect(domainLabel('climate-disaster')).toBe('closest domain: climate & disaster')
    expect(domainLabel(null)).toBe('untyped')
  })

  it('never renders a press-silence claim', () => {
    expect(divergenceLabel(item('a', 0.4, 10))).toBe(
      'more attention than coverage in Atlas')
    expect(divergenceLabel({ ...item('a', 0.4, 10), is_new: true })).toBe(
      'no Atlas coverage for this domain in 7 days')
    expect(divergenceLabel(item('a', -0.2, 10))).toBe(
      'more coverage than attention in Atlas')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend-v2 && npx vitest run src/lib/attentionDivergence.test.ts`
Expected: FAIL — cannot resolve `./attentionDivergence`

- [ ] **Step 3: Write minimal implementation**

```ts
// frontend-v2/src/lib/attentionDivergence.ts
// Client shaping for attention-coverage-divergence-v1.
//
// Every label here is a statement about ATLAS's corpus. Nothing in this file
// may claim the press is silent — measured 2026-07-22, 5 of 5 such claims
// would have been false.

export interface DivergenceItem {
  query: string
  country_code: string
  script: string
  attention_volume: number
  attention_rank: number | null
  domain: string | null
  domain_margin: number | null
  noise_class: string | null
  coverage_count: number
  coverage_samples: { headline: string; source: string }[]
  /** Headlines Atlas holds for this country in the window. Context only —
   *  never a gate. The retired info-desert floor gated on it and was inverted. */
  press_supply: number
  verify_url: string
  divergence: number
  is_new: boolean
  reason_codes: string[]
}

const DOMAIN_LABELS: Record<string, string> = {
  'climate-disaster': 'climate & disaster',
  'conflict-security': 'conflict & security',
  'economic-stress': 'economic stress',
  'economy-resources': 'economy & resources',
  'governance-rights': 'governance & rights',
  'information-environment': 'information environment',
  'migration-humanitarian': 'migration & humanitarian',
  'political-legitimacy': 'political legitimacy',
  'public-health': 'public health',
  'resources-energy': 'resources & energy',
  'social-unrest-labor': 'social unrest & labour',
  'technology-infrastructure': 'technology & infrastructure',
  'culture-society': 'culture & society',
}

/** Hedged on purpose: the specific category is measurably unreliable, only the
 *  domain is stable, so the label says "closest", never asserts. */
export function domainLabel(domain: string | null): string {
  if (!domain) return 'untyped'
  return `closest domain: ${DOMAIN_LABELS[domain] ?? domain.replace(/-/g, ' ')}`
}

export function divergenceLabel(item: DivergenceItem): string {
  if (item.is_new) return 'no Atlas coverage for this domain in 7 days'
  return item.divergence > 0
    ? 'more attention than coverage in Atlas'
    : 'more coverage than attention in Atlas'
}

export function topDivergent(items: DivergenceItem[], limit: number): DivergenceItem[] {
  return [...items]
    .sort((a, b) => (b.divergence - a.divergence) ||
                    (b.attention_volume - a.attention_volume))
    .slice(0, limit)
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend-v2 && npx vitest run src/lib/attentionDivergence.test.ts`
Expected: PASS — 4 passed

- [ ] **Step 5: Commit**

```bash
git add frontend-v2/src/lib/attentionDivergence.ts frontend-v2/src/lib/attentionDivergence.test.ts
git commit -m "feat(attention): pure client shaping for divergence-v1"
```

---

## Task 11: L1 surfaces — country band and global Brief section

**Files:**
- Modify: `frontend-v2/src/components/BriefNewspaper.tsx`

- [ ] **Step 1: Add the fetch and state, beside the existing coverage-gap band**

```tsx
const [divergence, setDivergence] = useState<DivergenceItem[]>([])
useEffect(() => {
  let ignore = false
  const url = `${API_BASE}/api/v2/attention/divergence?hours=24&limit=6` +
    (countryFilter ? `&country=${countryFilter}` : '')
  fetch(url)
    .then(r => (r.ok ? r.json() : null))
    .then(d => { if (!ignore) setDivergence(topDivergent(d?.items ?? [], 6)) })
    .catch(() => { if (!ignore) setDivergence([]) })   // honest absence
  return () => { ignore = true }
}, [countryFilter])
```

- [ ] **Step 2: Render the band — country door and global share one renderer**

```tsx
{divergence.length > 0 && (
  <section className="brief-divergence">
    <h3 className="brief-divergence-title">
      {countryFilter ? 'ATTENTION WITHOUT COVERAGE' : 'ATTENTION WITHOUT COVERAGE · GLOBAL'}
    </h3>
    <p className="brief-divergence-standfirst">
      What people are searching for, measured against what Atlas is covering.
      This compares two things Atlas measures — it is not a claim about what
      the press published.
    </p>
    {divergence.map(item => (
      <article key={`${item.country_code}-${item.query}`} className="brief-divergence-row">
        <span className="bdr-query">{item.query}</span>
        <span className="bdr-domain">{domainLabel(item.domain)}</span>
        <span className="bdr-state">{divergenceLabel(item)}</span>
        <a className="bdr-verify" href={item.verify_url}
           target="_blank" rel="noopener noreferrer">check outside Atlas ↗</a>
      </article>
    ))}
  </section>
)}
```

- [ ] **Step 3: Add the styles**

```css
/* BriefNewspaper.css */
.brief-divergence { margin-top: 1.5rem; border-top: 1px solid var(--border-subtle); padding-top: 1rem; }
.brief-divergence-title { font-size: 0.78rem; letter-spacing: 0.08em; color: var(--text-secondary); }
.brief-divergence-standfirst { font-size: 0.8rem; color: var(--text-tertiary); max-width: 60ch; }
.brief-divergence-row { display: flex; flex-wrap: wrap; gap: 0.5rem 0.75rem; padding: 0.4rem 0; align-items: baseline; }
.bdr-query { font-weight: 600; overflow-wrap: anywhere; }
.bdr-domain, .bdr-state { font-size: 0.75rem; color: var(--text-tertiary); }
.bdr-verify { font-size: 0.75rem; color: var(--accent); text-decoration: none; }
```

- [ ] **Step 4: Verify in the browser**

Run: `cd frontend-v2 && npm run build`
Then open the preview at `/brief` and `/brief?country=MX`.
Expected: band renders in both, console clean, no horizontal overflow at 375px.

- [ ] **Step 5: Commit**

```bash
git add frontend-v2/src/components/BriefNewspaper.tsx frontend-v2/src/components/BriefNewspaper.css
git commit -m "feat(brief): attention-without-coverage band, country and global"
```

---

## Task 12: L2 — restructure AnomalyPanel's PUBLIC ATTENTION

**Files:**
- Modify: `frontend-v2/src/components/AnomalyPanel.tsx:241-317`

Per Pedro: **no new dock tab.** The PUBLIC ATTENTION and forum-discussion
sections already *are* the public-attention surface; today they render raw
Trends[S] / Wiki[W] / Forum[F] lists. They become the interpreted view.

- [ ] **Step 1: Fetch divergence scoped to the same country the panel already resolves**

```tsx
const [divergence, setDivergence] = useState<DivergenceItem[]>([])
useEffect(() => {
  let ignore = false
  const url = `${API_BASE}/api/v2/attention/divergence?hours=24&limit=8` +
    (scopeCountry ? `&country=${scopeCountry}` : '')
  fetch(url)
    .then(r => (r.ok ? r.json() : null))
    .then(d => { if (!ignore) setDivergence(d?.items ?? []) })
    .catch(() => { if (!ignore) setDivergence([]) })
  return () => { ignore = true }
}, [scopeCountry])
```

- [ ] **Step 2: Annotate each attention row with its coverage state**

Keep the existing `[S]` / `[W]` / `[F]` badges and list, and append a coverage
chip to any row whose query matches a divergence item:

```tsx
const coverageOf = (title: string) =>
  divergence.find(d => d.query.toLowerCase() === title.toLowerCase())

// inside the existing attention row render:
{(() => {
  const d = coverageOf(item.title)
  if (!d) return null
  return (
    <span className="ap-coverage-chip"
          data-tip={`${domainLabel(d.domain)} — ${divergenceLabel(d)}. Atlas holds ${d.coverage_count} matching headlines.`}>
      {d.coverage_count === 0 ? 'no Atlas coverage' : `${d.coverage_count} in Atlas`}
    </span>
  )
})()}
```

- [ ] **Step 3: Add the styles**

```css
/* AnomalyPanel.css */
.ap-coverage-chip {
  font-size: 0.68rem; padding: 0.05rem 0.35rem; border-radius: 3px;
  background: var(--surface-raised); color: var(--text-tertiary); margin-left: 0.4rem;
}
```

- [ ] **Step 4: Verify in the browser**

Run: `cd frontend-v2 && npm run build`
Open `/app`, focus a country, and confirm the PUBLIC ATTENTION section shows
coverage chips and re-scopes with focus. Expected: chips present, console clean,
forum section unchanged.

- [ ] **Step 5: Commit**

```bash
git add frontend-v2/src/components/AnomalyPanel.tsx frontend-v2/src/components/AnomalyPanel.css
git commit -m "feat(l2): PUBLIC ATTENTION becomes the interpreted coverage view"
```

---

## Task 13: Thread `public_demand` — read-only

**Files:**
- Modify: `backend/app/services/thread_intelligence.py:1668-1680`
- Test: `backend/tests/test_thread_public_demand.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_thread_public_demand.py
from app.services.thread_intelligence import build_public_demand


def test_public_demand_groups_countries_by_domain_match():
    rows = [{"country_code": "MX", "keyword": "inundaciones en nogales",
             "domain": "climate-disaster", "attention_volume": 1000},
            {"country_code": "BR", "keyword": "nivel do guaiba",
             "domain": "climate-disaster", "attention_volume": 500},
            {"country_code": "DE", "keyword": "wohngeld kuerzung",
             "domain": "economic-stress", "attention_volume": 100}]
    demand = build_public_demand(rows, domain="climate-disaster")
    assert [d["country_code"] for d in demand] == ["MX", "BR"]
    assert demand[0]["attention_volume"] == 1000


def test_public_demand_is_empty_for_an_unmatched_domain():
    assert build_public_demand([], domain="public-health") == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_thread_public_demand.py -v`
Expected: FAIL — `ImportError: cannot import name 'build_public_demand'`

- [ ] **Step 3: Replace the decorative LIKE join with the typed read**

In `thread_intelligence.py`, replace the `trends_query` block at line 1668 with:

```python
def build_public_demand(rows: list[dict], *, domain: str) -> list[dict]:
    """Countries whose TYPED public attention shares this thread's domain.

    SERVING ONLY. This does NOT enter rank_threads. Front-page ordering is never
    flipped without an A/B (Atlas law); the demand reading has not been measured
    against ranking quality yet.
    """
    matched = [r for r in rows if r.get("domain") == domain]
    matched.sort(key=lambda r: -(r.get("attention_volume") or 0))
    return [{"country_code": r["country_code"], "query": r["keyword"],
             "attention_volume": r.get("attention_volume") or 0}
            for r in matched]
```

and feed it from `public_attention_typed` instead of the English `LIKE`:

```python
demand_rows = [dict(r) for r in await conn.fetch(
    """SELECT country_code, keyword, domain, attention_volume
       FROM public_attention_typed
       WHERE day >= (CURRENT_DATE - 1) AND domain IS NOT NULL
       ORDER BY attention_volume DESC LIMIT 300""")]
public_demand = build_public_demand(demand_rows, domain=thread_domain)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest tests/test_thread_public_demand.py -v`
Expected: PASS — 2 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/thread_intelligence.py backend/tests/test_thread_public_demand.py
git commit -m "feat(threads): typed public_demand replaces the decorative LIKE chip"
```

---

## Task 14: Feed-acquisition work-list

**Files:**
- Create: `backend/scripts/attention_feed_worklist.py`

- [ ] **Step 1: Write the script**

```python
#!/usr/bin/env python3
"""Turn residual divergence into a feed-acquisition work-list for #235.

Not a confession that Atlas is blind — an ordered list of which domestic feed to
acquire next. Measured 2026-07-22: ingest_rss.py carries 200 domains, at most
one flagship national outlet per country, no regional press and no
Greek/Hebrew/Thai-language press. Colombia is eltiempo.com only; Mexico is
jornada.com.mx only; South Africa is empty.

Read-only. Usage: python -m scripts.attention_feed_worklist
"""
from __future__ import annotations

import asyncio
import os

import asyncpg

SQL = """
    SELECT p.country_code, p.script,
           COUNT(*)                                   AS attention_items,
           COUNT(*) FILTER (WHERE p.coverage_count = 0) AS uncovered,
           SUM(p.attention_volume)                    AS attention_volume,
           (SELECT COUNT(*) FROM signals_v2 s
             WHERE s.country_code = p.country_code
               AND s.timestamp > NOW() - INTERVAL '48 hours'
               AND s.source_family IS DISTINCT FROM 'social') AS press_supply
    FROM public_attention_typed p
    WHERE p.day >= (CURRENT_DATE - 1) AND p.domain IS NOT NULL
    GROUP BY p.country_code, p.script
    HAVING COUNT(*) FILTER (WHERE p.coverage_count = 0) >= 3
    ORDER BY uncovered DESC, attention_volume DESC
    LIMIT 40
"""


async def main() -> None:
    conn = await asyncpg.connect(os.environ["DATABASE_URL"], statement_cache_size=0)
    rows = await conn.fetch(SQL)
    await conn.close()
    print(f"{'CC':<4}{'SCRIPT':<12}{'UNCOV':>6}{'ITEMS':>7}{'PRESS/48h':>11}")
    for r in rows:
        print(f"{r['country_code']:<4}{r['script'][:11]:<12}"
              f"{r['uncovered']:>6}{r['attention_items']:>7}{r['press_supply']:>11}")
    print("\nHigh uncovered + low press supply = the next feed to acquire (#235).")


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Run it against prod**

Run: `cd backend && .venv/bin/python -m scripts.attention_feed_worklist`
Expected: a table of countries ordered by uncovered attention, printing without error.

- [ ] **Step 3: Commit**

```bash
git add backend/scripts/attention_feed_worklist.py
git commit -m "feat(attention): feed-acquisition work-list for #235"
```

---

## Task 15: Deploy and prod-smoke

- [ ] **Step 1: Run the full backend suite**

Run: `cd backend && .venv/bin/python -m pytest tests/ -q -k "attention or thread"`
Expected: all green

- [ ] **Step 2: Run the frontend suite and build**

Run: `cd frontend-v2 && npx vitest run && npm run build`
Expected: all tests pass, build succeeds under Node 24

- [ ] **Step 3: Deploy the backend**

Run: `./scripts/deploy-fly-api.sh`
Expected: deploy completes, health check passes

- [ ] **Step 4: Prod smoke**

```bash
curl -s 'https://atlas-api-pedro.fly.dev/api/v2/attention/divergence?country=MX&hours=24' | jq '{contract, n_items: (.items|length), n_tray: (.tray|length), top: .items[0].query, note: .notes[-1]}'
```

Expected: `contract` is `attention-coverage-divergence-v1`, items and tray both
present, and the honesty note is the last entry.

```bash
curl -s 'https://atlas-api-pedro.fly.dev/api/v2/attention/silent-risks' -o /dev/null -w '%{http_code}\n'
```

Expected: `404` — the old endpoint is retired.

- [ ] **Step 5: Update CLAUDE.md and commit**

Add a dated session block recording: the metric, the three retired claims
(press-silence, info-desert floor, ensemble), the measured thresholds and their
calibration date, and the dependency on the GDELT entity fix.

```bash
git add CLAUDE.md
git commit -m "docs: attention-coverage divergence shipped"
```
