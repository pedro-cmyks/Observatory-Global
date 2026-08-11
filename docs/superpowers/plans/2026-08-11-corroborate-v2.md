# Corroborate-v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make corroboration independence MEASURED, not asserted — ownership grouping, attribution/paraphrase detection, temporal window, locale numerals, anti-template guard — per the approved spec `docs/superpowers/specs/2026-08-11-corroborate-v2-design.md`, gated on G-HAARETZ / G-STATE / G-LOCALE / G-TEMPLATE / G-NO-REGRESIÓN.

**Architecture:** All five changes land in the two existing pure-math modules (`app/services/corroboration.py`, `app/services/article_read.py`) plus one new export in `app/services/source_tiers.py`. Routers only thread parameters. Frontend mirrors `extractFigure` and renders the new honest labels. Zero new LLM calls in any hot path. The regression sample is frozen in Task 0 BEFORE any behavior change (pre-registration discipline).

**Tech Stack:** Python/FastAPI + pytest (backend), TypeScript/React + vitest (frontend). No new dependencies.

**Ordering constraint:** Task 0 MUST complete (sample frozen + committed) before Tasks 2-8 change any behavior. Tasks 1-6 are pure-module work and independent of each other after Task 0. Task 7 depends on 1+2+5. Task 8 depends on 3+4+5+6 contracts. Task 9 last.

**Council witnesses (the fixtures):**
- C-N18: crossread stamped "2 independent sources" over THREE rewrites of one Haaretz report whose own quotes say "According to Haaretz".
- M-N18: ria.ru + interfax counted as 2 of "20 independently-operated outlets".
- C-N17: Indonesian "1.700" parsed as 1.7 → best match became the top contradiction.
- T-N19/DESK-N23: a Mali ambush corroborating a Gaza headline (template shape).
- C-N22: a 6-week-old receipt backing a verdict dated today, indistinguishable.

---

### Task 0: Freeze the G-NO-REGRESIÓN sample (BEFORE any behavior change)

**Files:**
- Create: `backend/scripts/corroborate_v2_gate.py`
- Create (output, committed): `docs/research/corroborate-v2/2026-08-11-regression-sample.json`

The gate script has two modes: `--freeze` (Task 0: sample 20 currently-CORROBORATED claims from live prod and record their current counts) and `--check` (Task 9: replay the frozen claims against the new code and verify count drop ≤15%).

- [ ] **Step 1: Write the script**

```python
"""Corroborate-v2 pre-registered gate (spec 2026-08-11-corroborate-v2-design.md).

--freeze : sample 20 claims that TODAY produce status='corroborated' via
           corroborate_claim against live prod; save claim + counts to the
           fixture. Run BEFORE any corroborate-v2 behavior change.
--check  : replay the frozen claims with current code; PASS iff total
           corroborating count across the sample drops ≤15% vs frozen
           (G-NO-REGRESIÓN). Per-claim deltas reported either way.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

FIXTURE = Path(__file__).resolve().parents[2] / (
    "docs/research/corroborate-v2/2026-08-11-regression-sample.json")

# Diverse, currently-servable claims: recent gate-kept headlines across ≥8
# countries. Sampled via SQL at freeze time — seeded ORDER BY so re-freeze is
# deterministic on the same day's data.
_SAMPLE_SQL = """
    SELECT DISTINCT ON (s.country_code)
           s.headline, s.country_code, s.source_lang
    FROM signals_v2 s
    JOIN signal_topic_assignments a ON a.signal_id = s.id AND a.gate_kept
    WHERE s.headline IS NOT NULL
      AND s.timestamp > now() - interval '48 hours'
      AND length(s.headline) BETWEEN 40 AND 200
    ORDER BY s.country_code, s.id
    LIMIT 40
"""


async def _run(mode: str) -> int:
    import asyncpg
    from app.services.corroboration import corroborate_claim

    dsn = os.environ["DATABASE_URL"]
    conn = await asyncpg.connect(dsn, statement_cache_size=0)
    try:
        if mode == "freeze":
            rows = await conn.fetch(_SAMPLE_SQL)
            frozen = []
            for r in rows:
                res = await corroborate_claim(
                    headline=r["headline"], country=r["country_code"],
                    conn=conn)
                v = res.get("verdict") or {}
                if v.get("status") == "corroborated":
                    frozen.append({
                        "headline": r["headline"],
                        "country": r["country_code"],
                        "source_lang": r["source_lang"],
                        "corroborating": v.get("corroborating", 0),
                    })
                if len(frozen) >= 20:
                    break
            FIXTURE.parent.mkdir(parents=True, exist_ok=True)
            FIXTURE.write_text(json.dumps(
                {"frozen_at": "2026-08-11", "claims": frozen}, indent=2))
            print(f"frozen {len(frozen)} corroborated claims -> {FIXTURE}")
            return 0 if len(frozen) >= 15 else 1

        data = json.loads(FIXTURE.read_text())
        base = sum(c["corroborating"] for c in data["claims"])
        now_total = 0
        for c in data["claims"]:
            res = await corroborate_claim(
                headline=c["headline"], country=c["country"], conn=conn)
            v = res.get("verdict") or {}
            n = v.get("corroborating", 0)
            now_total += n
            print(f"  {n:>3} (was {c['corroborating']:>3})  {c['headline'][:70]}")
        drop = 0.0 if base == 0 else (base - now_total) / base
        print(f"\nG-NO-REGRESIÓN: frozen={base} now={now_total} "
              f"drop={drop:.1%} (bar ≤15%)")
        print("PASS" if drop <= 0.15 else "FAIL")
        return 0 if drop <= 0.15 else 1
    finally:
        await conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--freeze", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    sys.exit(asyncio.run(_run("freeze" if a.freeze else "check")))
```

- [ ] **Step 2: Run freeze against prod**

Run: `cd backend && set -a && source /Users/pedro/AtlasLocalWorker/.env && set +a && .venv/bin/python scripts/corroborate_v2_gate.py --freeze`
Expected: `frozen N corroborated claims` with N ≥ 15 (DOC 2.0 may throttle some — the Atlas lanes still yield corroborated claims; if N < 15, re-run once after 5 min: the doc20 cooldown clears). Caveat: claims whose corroboration relies on doc20 will vary between runs — that is WHY the fixture freezes the counts.

- [ ] **Step 3: Commit script + fixture**

```bash
git add backend/scripts/corroborate_v2_gate.py docs/research/corroborate-v2/2026-08-11-regression-sample.json
git commit -m "gate(corroborate-v2): freeze G-NO-REGRESIÓN sample BEFORE behavior changes"
```

---

### Task 1: `ownership_group()` in source_tiers.py

**Files:**
- Modify: `backend/app/services/source_tiers.py` (after the `STATE` dict, ~line 108)
- Test: `backend/tests/test_source_tiers.py` (append)

- [ ] **Step 1: Write the failing tests**

```python
def test_ownership_group_state_outlets_share_group():
    from app.services.source_tiers import ownership_group
    assert ownership_group("ria.ru") == "state:ru"
    assert ownership_group("tass.com") == "state:ru"
    assert ownership_group("https://www.rt.com/news/x") == "state:ru"
    assert ownership_group("xinhuanet.com") == "state:cn"
    assert ownership_group("presstv.ir") == "state:ir"

def test_ownership_group_none_for_independent_press():
    from app.services.source_tiers import ownership_group
    assert ownership_group("cnn.com") is None
    assert ownership_group("reuters.com") is None
    assert ownership_group(None) is None

def test_state_groups_cover_exactly_the_state_dict():
    from app.services.source_tiers import STATE, STATE_GROUPS
    assert set(STATE_GROUPS) == set(STATE)
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && .venv/bin/python -m pytest tests/test_source_tiers.py -q -k ownership_group`
Expected: FAIL (ImportError: cannot import name 'ownership_group')

- [ ] **Step 3: Implement**

Add after the `STATE` dict in `source_tiers.py`:

```python
# Corroborate-v2 R1: ownership groups. Outlets in one state apparatus are ONE
# voice for independence counting (ria+interfax+tass corroborating each other
# is one government speaking three times). Keys MUST mirror STATE exactly
# (test-frozen) so the tier chip and the independence math never disagree.
STATE_GROUPS = {
    "rt.com": "ru", "sputniknews.com": "ru", "sputnikglobe.com": "ru",
    "tass.com": "ru", "tass.ru": "ru", "ria.ru": "ru", "1tv.ru": "ru",
    "xinhuanet.com": "cn", "news.cn": "cn", "cgtn.com": "cn",
    "globaltimes.cn": "cn", "people.com.cn": "cn", "chinadaily.com.cn": "cn",
    "cctv.com": "cn",
    "presstv.ir": "ir", "irna.ir": "ir", "tasnimnews.com": "ir",
    "mehrnews.com": "ir",
    "trtworld.com": "tr", "aa.com.tr": "tr",
    "kcna.kp": "kp",
    "granma.cu": "cu", "prensa-latina.cu": "cu",
    "telesurtv.net": "ve",
    "sana.sy": "sy",
}


def ownership_group(source: str | None) -> str | None:
    """Ownership-group key for independence counting, or None when the outlet
    has no known shared owner. Only state apparatuses are grouped in v2 —
    commercial conglomerates need a measured list before they join."""
    dom = _domain_of(source)
    if not dom:
        return None
    for d, g in STATE_GROUPS.items():
        if dom == d or dom.endswith("." + d):
            return f"state:{g}"
    return None
```

- [ ] **Step 4: Run tests + commit**

Run: `.venv/bin/python -m pytest tests/test_source_tiers.py -q` → all PASS.

```bash
git add backend/app/services/source_tiers.py backend/tests/test_source_tiers.py
git commit -m "feat(corroborate-v2 R1): ownership_group — state outlets share one voice"
```

---

### Task 2: Ownership-aware `independence()` + `pin_status` (G-STATE)

**Files:**
- Modify: `backend/app/services/corroboration.py:123-168` (`independence`, `pin_status`)
- Test: `backend/tests/test_corroboration.py` (append; file exists — follow its fixture style)

- [ ] **Step 1: Write the failing tests**

```python
def test_g_state_ria_interfax_tass_collapse_to_one_voice():
    """G-STATE (spec pre-registered): same state apparatus = ONE voice."""
    from app.services.corroboration import independence
    from app.services.source_tiers import ownership_group
    arts = [
        {"title": "Strikes hit depot in western region overnight", "outlet": "ria.ru"},
        {"title": "Military reports depot strike in western region", "outlet": "tass.com"},
        {"title": "Western region depot hit, officials say details", "outlet": "rt.com"},
        {"title": "Depot fire after overnight raid, residents flee", "outlet": "cnn.com"},
    ]
    out = independence(arts, group_fn=ownership_group)
    assert out["independent_outlets"] == 4          # outlets stay visible
    assert out["independent_voices"] == 2           # state:ru + cnn.com
    assert out["state_collapsed"] == 2              # 3 state outlets -> 1 voice
    groups = {c["outlet"]: c.get("ownership_group") for c in out["citations"]}
    assert groups["ria.ru"] == "state:ru" and groups["cnn.com"] is None

def test_independence_without_group_fn_backward_compatible():
    from app.services.corroboration import independence
    arts = [{"title": "A story about x y z", "outlet": "a.com"},
            {"title": "Different account of x", "outlet": "b.com"}]
    out = independence(arts)
    assert out["independent_voices"] == out["independent_outlets"] == 2

def test_pin_status_counts_voices_and_names_collapse():
    from app.services.corroboration import pin_status
    status, note = pin_status(2, True, outlets=4, state_collapsed=2)
    assert status == "unverified"       # 2 voices < 3, even though 4 outlets
    assert "state" in note
    status, _ = pin_status(3, True, outlets=3, state_collapsed=0)
    assert status == "established"
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/python -m pytest tests/test_corroboration.py -q -k "g_state or voices or collapse"`
Expected: FAIL (TypeError: unexpected keyword 'group_fn')

- [ ] **Step 3: Implement**

Replace `independence()` (corroboration.py:123-142):

```python
def independence(articles: list[dict], *, group_fn=None) -> dict[str, Any]:
    """The G2 rule as a number, ownership-aware (corroborate-v2 R1).
    Cluster near-identical titles (wire copies -> one representative); count
    DISTINCT outlets across representatives; THEN collapse outlets that share
    an ownership group (group_fn, e.g. source_tiers.ownership_group) into one
    VOICE. 20 reprints of one wire = 1 outlet; ria+tass+rt each writing their
    own = 3 outlets but 1 voice. Citations keep one row per outlet (receipts
    stay visible) and carry `ownership_group` so the render can say why."""
    clusters = cluster_syndicated(articles)
    rep_outlets: list[str] = []
    citations: list[dict] = []
    voices: list[str] = []
    for members in clusters:
        rep = members[0]
        outlet = (rep.get("outlet") or "").lower()
        if not outlet or outlet in rep_outlets:
            continue
        rep_outlets.append(outlet)
        group = group_fn(outlet) if group_fn else None
        citations.append({**rep, "ownership_group": group})
        voice_key = group or outlet
        if voice_key not in voices:
            voices.append(voice_key)
    return {
        "independent_outlets": len(rep_outlets),
        "independent_voices": len(voices),
        "state_collapsed": len(rep_outlets) - len(voices),
        "total_articles": len(articles),
        "syndicated_clusters": sum(1 for m in clusters if len(m) > 1),
        "citations": citations,
    }
```

Replace `pin_status()` (the count it judges is now VOICES; keep the signature's first positional so old tests read naturally):

```python
def pin_status(
    independent_voices: int,
    search_available: bool,
    *,
    applicable: bool = True,
    outlets: int | None = None,
    state_collapsed: int = 0,
) -> tuple[str, str]:
    """(status, note) from the independence count — glass-box, no judgment.
    v2: the bar is independent VOICES (ownership-collapsed), and the note
    names the collapse when it changed the number."""
    if not applicable:
        return (
            "not_applicable",
            "metadata-only context pin — no frozen evidence claim to corroborate",
        )
    if not search_available:
        return ("unverified",
                "web-search lane unavailable — corroboration not measured")
    collapse_note = ""
    if state_collapsed > 0 and outlets is not None:
        collapse_note = (f" ({outlets} outlets; same-state outlets "
                         "counted as one voice)")
    if independent_voices >= ESTABLISHED_MIN_OUTLETS:
        return ("established",
                f"{independent_voices} independent voices"
                f"{collapse_note or ' (syndicated copies collapsed)'}")
    if independent_voices == 0:
        return ("unverified", "no matching web coverage found in the window")
    return ("unverified",
            f"only {independent_voices} independent voice(s)"
            f"{collapse_note} — insufficient corroboration; "
            "treat as single-sourced")
```

- [ ] **Step 4: Run the module's full suite**

Run: `.venv/bin/python -m pytest tests/test_corroboration.py -q`
Expected: new tests PASS. Pre-existing `pin_status` tests may fail on the note-string change — update ONLY their expected strings (the status logic is unchanged for the ungrouped path); if any pre-existing test fails on a STATUS (not string), stop and re-read — that would be a real regression.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/corroboration.py backend/tests/test_corroboration.py
git commit -m "feat(corroborate-v2 R1): independence counts VOICES — G-STATE fixture passes"
```

---

### Task 3: Locale-aware `extract_figure` (G-LOCALE)

**Files:**
- Modify: `backend/app/services/corroboration.py:218-233` (`_FIGURE_RE`, `extract_figure`) + `classify_relation` + the three `rows_to_*`/`articles_to_*` builders + `corroborate_claim`
- Test: `backend/tests/test_corroboration.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_g_locale_indonesian_dot_grouping():
    """G-LOCALE (spec): '1.700' in a comma-decimal locale is 1700, not 1.7."""
    from app.services.corroboration import extract_figure
    assert extract_figure("1.700 orang tewas akibat gempa", lang="id") == 1700.0
    assert extract_figure("1.700 muertos según el gobierno", lang="es") == 1700.0

def test_extract_figure_unambiguous_grouping_any_lang():
    from app.services.corroboration import extract_figure
    assert extract_figure("1.234.567 affected") == 1234567.0     # two dot groups
    assert extract_figure("1.234.567,89 total", lang="de") == 1234567.89
    assert extract_figure("1,234,567.89 total") == 1234567.89

def test_extract_figure_decimal_preserved():
    from app.services.corroboration import extract_figure
    assert extract_figure("magnitude 7.6 earthquake") == 7.6            # en default
    assert extract_figure("magnitud 7,6 del sismo", lang="es") == 7.6   # comma decimal
    assert extract_figure("1.700 dead") == 1.7   # lang unknown -> conservative, unchanged

def test_g_locale_relation_no_longer_inverts():
    """The C-N17 witness: same toll in two locales must corroborate."""
    from app.services.corroboration import classify_relation, extract_figure
    claim_terms = ["earthquake", "sulawesi", "dead", "1700"]
    claim_figure = 1700.0
    rel = classify_relation(
        claim_terms, claim_figure,
        "Gempa Sulawesi: 1.700 orang tewas, ribuan mengungsi",
        candidate_lang="id")
    assert rel != "contradicts"
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/python -m pytest tests/test_corroboration.py -q -k locale`
Expected: FAIL (TypeError: extract_figure() got unexpected keyword 'lang')

- [ ] **Step 3: Implement**

Replace the figure block (corroboration.py:216-233):

```python
# Locale numeral discipline (corroborate-v2 F1, council C-N17: Indonesian
# "1.700" parsed as 1.7 made the best match the top contradiction). Languages
# that write decimals with a COMMA and group thousands with a DOT:
_COMMA_DECIMAL_LANGS = frozenset({
    "es", "pt", "de", "fr", "it", "id", "in", "tr", "ru", "uk", "nl", "da",
    "sv", "no", "nb", "nn", "fi", "pl", "cs", "sk", "el", "ro", "hu", "vi",
    "az", "kk", "sr", "hr", "bg", "ca", "sl", "lt", "lv", "et", "mk", "sq",
    "bs", "ka", "hy", "be",
})
_FIGURE_TOKEN_RE = re.compile(r"\d[\d.,]*\d|\d")


def _parse_figure_token(tok: str, *, comma_decimal: bool) -> float | None:
    """One numeric token -> float under the locale's separator convention.
    Universal rule first: when BOTH separators appear, the LAST one is the
    decimal mark. Then per-locale: a single separator followed by exactly
    three digits is thousands-grouping in that locale's grouping character;
    otherwise it is the decimal mark. Unknown-locale single-dot stays decimal
    (conservative: preserves v1 behavior for English)."""
    tok = tok.strip(".,")
    if not tok:
        return None
    has_dot, has_comma = "." in tok, "," in tok
    try:
        if has_dot and has_comma:
            dec = "." if tok.rfind(".") > tok.rfind(",") else ","
            grp = "," if dec == "." else "."
            return float(tok.replace(grp, "").replace(dec, "."))
        if has_dot:
            parts = tok.split(".")
            if len(parts) > 2:                      # 1.234.567 — unambiguous
                return float(tok.replace(".", ""))
            if comma_decimal and len(parts[1]) == 3:
                return float(tok.replace(".", ""))  # id/es/de: 1.700 = 1700
            return float(tok)
        if has_comma:
            parts = tok.split(",")
            if len(parts) > 2:                      # 1,234,567 — unambiguous
                return float(tok.replace(",", ""))
            if comma_decimal:
                return float(tok.replace(",", "."))  # es: 7,6 = 7.6
            if len(parts[1]) == 3:
                return float(tok.replace(",", ""))   # en: 1,700 = 1700
            return float(tok.replace(",", "."))
        return float(tok)
    except ValueError:
        return None


def extract_figure(text: str | None, *, lang: str | None = None) -> float | None:
    """First number in the text under the source language's numeral locale.
    Mirrors claimLedger.ts extractFigure (which gains the same lang param in
    this change) so a headline's toll parses identically on both ends."""
    if not text:
        return None
    m = _FIGURE_TOKEN_RE.search(text)
    if not m:
        return None
    comma_decimal = (lang or "").strip().lower()[:2] in _COMMA_DECIMAL_LANGS
    return _parse_figure_token(m.group(0), comma_decimal=comma_decimal)
```

Delete the old `_FIGURE_RE` definition. Thread the language through:
- `classify_relation(..., *, similarity=None, candidate_lang=None)` → `cand_figure = extract_figure(candidate_headline, lang=candidate_lang)`.
- `articles_to_doc20_matches`: pass `candidate_lang=(a.get("language") or None)` (DOC 2.0 artlist carries `language`; lowercase it).
- `rows_to_hot_matches`: pass `candidate_lang=m.get("source_lang")` (check `fetch_semantic_signal_matches` output in `research_semantic.py` — if it does not carry `source_lang`, ADD it to that SELECT; it reads signals_v2 which has the column).
- `rows_to_archive_matches`: check `historical_evidence_samples` columns (`\d` via psql or the migration file); if `source_lang` absent, pass `candidate_lang=None` — honest absence, do NOT fabricate.
- `corroborate_claim(..., lang: str | None = None)` → `figure = extract_figure(headline, lang=lang)`; router `CorroborateRequest` gains `lang: str | None = Field(default=None, max_length=8)` and passes it.

- [ ] **Step 4: Run + commit**

Run: `.venv/bin/python -m pytest tests/test_corroboration.py -q` → PASS.

```bash
git add backend/app/services/corroboration.py backend/app/routers/corroborate.py backend/app/services/research_semantic.py backend/tests/test_corroboration.py
git commit -m "fix(corroborate-v2 F1): locale-aware figures — G-LOCALE fixture passes (C-N17)"
```

---

### Task 4: Anti-template guard (G-TEMPLATE)

**Files:**
- Modify: `backend/app/services/corroboration.py` (`classify_relation`, new `_TEMPLATE_TERMS`/`anchor_overlap`/`_mostly_latin`; `citation_verdict` counts)
- Test: `backend/tests/test_corroboration.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_g_template_mali_does_not_corroborate_gaza():
    """G-TEMPLATE (spec): same casualty template, disjoint entities."""
    from app.services.corroboration import classify_relation, extract_claim_terms
    claim = extract_claim_terms("Israeli strike kills 12 in Gaza refugee camp")
    rel = classify_relation(
        claim["terms"], 12.0,
        "Ambush kills 12 soldiers in northern Mali",
        similarity=0.87)          # template shapes embed close — the witness
    assert rel == "template_match"

def test_template_guard_spares_true_same_event():
    from app.services.corroboration import classify_relation, extract_claim_terms
    claim = extract_claim_terms("Israeli strike kills 12 in Gaza refugee camp")
    rel = classify_relation(
        claim["terms"], 12.0,
        "Gaza refugee camp hit by Israeli strike, 12 dead")
    assert rel == "corroborates"

def test_template_guard_exempts_cross_script_semantic():
    """Cross-language TRUE matches share zero Latin tokens — the semantic
    lane stays alive across scripts (anchor requirement is lexical)."""
    from app.services.corroboration import classify_relation, extract_claim_terms
    claim = extract_claim_terms("Israeli strike kills 12 in Gaza refugee camp")
    rel = classify_relation(
        claim["terms"], None,
        "غارة إسرائيلية تقتل 12 في مخيم للاجئين بغزة",
        similarity=0.90)
    assert rel == "corroborates"

def test_citation_verdict_excludes_template_matches():
    from app.services.corroboration import citation_verdict
    matches = [
        {"relation": "corroborates", "official": False},
        {"relation": "template_match", "official": True},
    ]
    v = citation_verdict(matches)
    assert v["corroborating"] == 1
    assert v["template_matches"] == 1
    assert "template" in v["note"]
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/python -m pytest tests/test_corroboration.py -q -k template`
Expected: FAIL (first test returns 'corroborates'/'contradicts', not 'template_match')

- [ ] **Step 3: Implement**

Add near the relation constants:

```python
# Anti-template guard (corroborate-v2 F2, council T-N19/DESK-N23: a Mali
# ambush corroborated a Gaza headline). Casualty/disaster boilerplate that
# two UNRELATED events share; matching on these alone is matching the
# TEMPLATE, not the event. A same-event verdict needs at least one shared
# ANCHOR term (a non-template, non-numeric token) — except cross-script
# semantic matches, where lexical overlap is impossible by construction.
_TEMPLATE_TERMS = frozenset({
    "kill", "kills", "killed", "killing", "dead", "death", "deaths", "die",
    "dies", "died", "toll", "casualties", "victims", "injured", "wounded",
    "wounds", "hurt", "attack", "attacks", "attacked", "strike", "strikes",
    "struck", "blast", "blasts", "explosion", "bomb", "bombing", "shooting",
    "shot", "gunmen", "ambush", "raid", "clash", "clashes", "soldiers",
    "troops", "forces", "militants", "fighters", "police", "officials",
    "people", "least", "several", "dozens", "hundreds", "thousands",
    "missing", "rescue", "rescued", "survivors", "damage", "destroyed",
    "fire", "fires", "flood", "floods", "flooding", "earthquake", "quake",
    "storm", "crash", "crashes", "collapse", "collapsed",
})


def anchor_overlap(claim_terms: list[str], candidate_text: str | None) -> int:
    """Count of shared NON-template, non-numeric terms — the event's proper
    anchors (places, actors, distinctive nouns)."""
    cand = set(_tokens(candidate_text or ""))
    return sum(
        1 for t in set(claim_terms)
        if t in cand and t not in _TEMPLATE_TERMS and not t.isdigit()
    )


_LATIN_LETTER_RE = re.compile(r"[a-zA-Z]")
_NON_LATIN_LETTER_RE = re.compile(r"[^\W\d_a-zA-Z]", re.UNICODE)


def _mostly_latin(text: str | None) -> bool:
    latin = len(_LATIN_LETTER_RE.findall(text or ""))
    other = len(_NON_LATIN_LETTER_RE.findall(text or ""))
    return latin >= other
```

Rewrite `classify_relation` (keeping the Task-3 `candidate_lang` param):

```python
def classify_relation(
    claim_terms: list[str],
    claim_figure: float | None,
    candidate_headline: str | None,
    *,
    similarity: float | None = None,
    candidate_lang: str | None = None,
) -> Relation:
    """MATH relation for one candidate against the claim. Same-event needs
    term recall OR semantic closeness AND at least one shared anchor term
    (F2 — template vocabulary alone never establishes the same event; a
    cross-script semantic match is exempt because lexical anchors cannot
    exist there). Same-event + conflicting figure = contradicts; same-event
    + matching/absent figure = corroborates; template-shaped closeness with
    no anchors = template_match (visible, never counted); weaker = context."""
    recall = term_recall(claim_terms, candidate_headline)
    semantic_same = similarity is not None and similarity >= SAME_EVENT_SIMILARITY
    same_event = recall >= SAME_EVENT_TERM_RECALL or semantic_same
    anchors = anchor_overlap(claim_terms, candidate_headline)
    cross_script = not _mostly_latin(candidate_headline)
    anchored = anchors > 0 or (semantic_same and cross_script)
    if same_event and not anchored:
        return "template_match"
    cand_figure = extract_figure(candidate_headline, lang=candidate_lang)
    fig_rel = figure_relation(claim_figure, cand_figure)
    if same_event and fig_rel == "contradicts":
        return "contradicts"
    if fig_rel == "corroborates" and same_event:
        return "corroborates"
    if recall >= CORROBORATE_TERM_RECALL or semantic_same:
        return "corroborates" if anchored else "template_match"
    return "context"
```

Update the `Relation` docstring alias comment to `'corroborates' | 'contradicts' | 'context' | 'template_match'`. In `citation_verdict`, add before the status logic:

```python
    template = [m for m in matches if m.get("relation") == "template_match"]
```

exclude them from `corr`/`contra` (they never were — the list comprehensions already filter by relation), add `"template_matches": len(template)` to the return dict, and when `template` is non-empty append `f"{len(template)} template-shaped match(es) set aside (shared casualty boilerplate, no shared event anchor)"` to `parts`.

- [ ] **Step 4: Run + commit**

Run: `.venv/bin/python -m pytest tests/test_corroboration.py -q` → PASS (if any pre-existing relation test breaks, inspect: a fixture whose claim/candidate share ONLY template terms was asserting a false corroboration — update it citing G-TEMPLATE, but a fixture with real anchors failing = your bug).

```bash
git add backend/app/services/corroboration.py backend/tests/test_corroboration.py
git commit -m "feat(corroborate-v2 F2): anti-template guard — G-TEMPLATE fixture passes (Mali≠Gaza)"
```

---

### Task 5: Temporal window — `aged_receipt` (C-N22)

**Files:**
- Modify: `backend/app/services/corroboration.py` (`citation_verdict` + a date parser; `corroborate_claim` return already flows through it)
- Test: `backend/tests/test_corroboration.py`

- [ ] **Step 1: Write the failing tests**

```python
import datetime as dt

def test_aged_receipts_marked_and_not_counted():
    """C-N22 (spec R3): a 6-week-old receipt cannot back a verdict dated today."""
    from app.services.corroboration import citation_verdict
    today = dt.date(2026, 8, 11)
    matches = [
        {"relation": "corroborates", "official": True, "date": "2026-06-28"},
        {"relation": "corroborates", "official": False, "date": "2026-08-10"},
        {"relation": "corroborates", "official": False, "date": "20260809T120000Z"},
        {"relation": "corroborates", "official": False, "date": None},
    ]
    v = citation_verdict(matches, today=today)
    assert v["corroborating"] == 3          # dateless is NOT aged (can't claim)
    assert v["aged"] == 1
    assert matches[0]["aged"] is True and matches[1]["aged"] is False
    assert "aged" in v["note"]

def test_all_aged_means_uncorroborated_today():
    from app.services.corroboration import citation_verdict
    today = dt.date(2026, 8, 11)
    v = citation_verdict(
        [{"relation": "corroborates", "official": False, "date": "2026-06-01"}],
        today=today)
    assert v["status"] == "uncorroborated"
    assert v["aged"] == 1
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/python -m pytest tests/test_corroboration.py -q -k aged`
Expected: FAIL (TypeError: unexpected keyword 'today')

- [ ] **Step 3: Implement**

```python
CITATION_WINDOW_DAYS = 7   # spec R3 — frozen at approval

_DOC20_DATE_RE = re.compile(r"^(\d{4})(\d{2})(\d{2})T")


def _match_date(raw: str | None):
    """Best-effort date from a match's `date` field: ISO 'YYYY-MM-DD[…]' or
    DOC 2.0 'YYYYMMDDTHHMMSSZ'. None when absent/unparseable — an undated
    receipt is never CLAIMED aged (honest: we can't measure what we don't
    have)."""
    import datetime as _dt
    if not raw:
        return None
    s = str(raw).strip()
    m = _DOC20_DATE_RE.match(s)
    if m:
        try:
            return _dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    try:
        return _dt.date.fromisoformat(s[:10])
    except ValueError:
        return None
```

`citation_verdict` gains `*, window_days: int = CITATION_WINDOW_DAYS, today=None`; at the top:

```python
    import datetime as _dt
    today = today or _dt.date.today()
    for m in matches:
        d = _match_date(m.get("date"))
        m["aged"] = bool(d and (today - d).days > window_days)
```

then `corr`/`contra` comprehensions add `and not m.get("aged")`; return dict gains `"aged": sum(1 for m in matches if m.get("aged"))` and `"window_days": window_days`; when aged corroborating/contradicting rows exist append to `parts`: `f"{n_aged} aged receipt(s) outside the {window_days}-day window (context only)"`.

- [ ] **Step 4: Run + commit**

Run: `.venv/bin/python -m pytest tests/test_corroboration.py -q` → PASS.

```bash
git add backend/app/services/corroboration.py backend/tests/test_corroboration.py
git commit -m "feat(corroborate-v2 R3): aged_receipt window — a 6-week receipt no longer backs today (C-N22)"
```

---

### Task 6: Attribution + quote-overlap in cross-read (G-HAARETZ)

**Files:**
- Modify: `backend/app/services/article_read.py` (new `attributed_outlet`, `quote_overlap`, `same_primary_source`; extend `source_signature` call path + `articles_independent` + `_INDEPENDENCE_LABEL` + `validate_cross`)
- Test: `backend/tests/test_article_read.py` (exists — follow its fixture style)

- [ ] **Step 1: Write the failing tests**

```python
def test_attributed_outlet_detects_media_attribution():
    from app.services.article_read import attributed_outlet
    quotes = [
        "According to Haaretz, the meeting took place on Sunday.",
        "The plan was first drafted in May, according to Haaretz.",
    ]
    assert attributed_outlet(quotes) == "haaretz"

def test_attributed_outlet_ignores_non_media():
    from app.services.article_read import attributed_outlet
    assert attributed_outlet(["According to officials, the toll rose."]) is None
    assert attributed_outlet(["según las autoridades, hubo daños"]) is None
    assert attributed_outlet([]) is None

def test_attributed_outlet_spanish_and_german():
    from app.services.article_read import attributed_outlet
    assert attributed_outlet(["Según Haaretz, la reunión ocurrió el domingo."]) == "haaretz"
    assert attributed_outlet(["Wie Bild berichtete, begann der Einsatz früh."]) == "bild"

def test_g_haaretz_three_rewrites_one_primary_source():
    """G-HAARETZ (spec pre-registered): three rewrites of one Haaretz report,
    each attributing to Haaretz, are ONE voice — not '2 independent sources'."""
    from app.services.article_read import articles_independent
    a = {"outlet_root": "sitea.com", "wire_sig": "meeting plan drafted may",
         "content_hash": "h1", "derivative_of": "haaretz"}
    b = {"outlet_root": "siteb.net", "wire_sig": "secret plan meeting sunday",
         "content_hash": "h2", "derivative_of": "haaretz"}
    indep, reason = articles_independent(a, b)
    assert indep is False and reason == "same_primary_source"

def test_derivative_of_the_other_articles_masthead():
    from app.services.article_read import articles_independent
    a = {"outlet_root": "haaretz.com", "wire_sig": "x", "content_hash": "h1",
         "derivative_of": None}
    b = {"outlet_root": "siteb.net", "wire_sig": "y", "content_hash": "h2",
         "derivative_of": "haaretz"}
    indep, reason = articles_independent(a, b)
    assert indep is False and reason == "same_primary_source"

def test_quote_overlap_same_primary():
    from app.services.article_read import quote_overlap
    q1 = ["The strike was carried out at dawn near the northern crossing point",
          "We had no warning whatsoever before the explosions began that morning"]
    q2 = ["Officials said the strike was carried out at dawn near the northern crossing point",
          "A resident said: We had no warning whatsoever before the explosions began that morning"]
    assert quote_overlap(q1, q2) >= 0.6

def test_quote_overlap_distinct_reporting():
    from app.services.article_read import quote_overlap
    q1 = ["The strike was carried out at dawn near the northern crossing point"]
    q2 = ["Hospitals reported forty arrivals within the first hour of the incident"]
    assert quote_overlap(q1, q2) == 0.0
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/python -m pytest tests/test_article_read.py -q -k "attributed or haaretz or quote_overlap or derivative"`
Expected: FAIL (ImportError)

- [ ] **Step 3: Implement**

Add after `articles_independent` in article_read.py:

```python
# ── Corroborate-v2 R2: paraphrase/attribution independence ───────────────────
# The C-N18 witness: three REWRITES of one Haaretz report — different bodies,
# different headlines, so content_hash/wire_sig/outlet_root all pass — whose
# own quotes say "According to Haaretz". Byte-identity catches syndication;
# this catches DERIVATION. Layer 1 is regex over the claims' verbatim quotes
# (cheap, pre-embedding); layer 2 is quote-text overlap. Precision-first:
# attribution to non-media actors (officials, police, ministries) never fires.

_ATTRIBUTION_RES = [
    re.compile(r"\baccording to (?:the )?([A-Z][\w'’.-]+(?: [A-Z][\w'’.-]+){0,3})"),
    re.compile(r"\b(?:first )?reported by (?:the )?([A-Z][\w'’.-]+(?: [A-Z][\w'’.-]+){0,3})"),
    re.compile(r"\b(?:as )?([A-Z][\w'’.-]+(?: [A-Z][\w'’.-]+){0,3}) (?:first )?reported\b"),
    re.compile(r"\bcit(?:ing|ed by) ([A-Z][\w'’.-]+(?: [A-Z][\w'’.-]+){0,3})"),
    # es
    re.compile(r"\b[Ss]egún (?:el diario |la agencia |el portal )?([A-Z][\w'’.-]+(?: [A-Z][\w'’.-]+){0,2})"),
    re.compile(r"\b[Ii]nformó ([A-Z][\w'’.-]+(?: [A-Z][\w'’.-]+){0,2})"),
    re.compile(r"\bcitando a ([A-Z][\w'’.-]+(?: [A-Z][\w'’.-]+){0,2})"),
    # de / fr
    re.compile(r"\b[Ww]ie ([A-Z][\w'’.-]+(?: [A-Z][\w'’.-]+){0,2}) berichtet"),
    re.compile(r"\bselon (?:le |la |l')?([A-Z][\w'’.-]+(?: [A-Z][\w'’.-]+){0,2})"),
]

# Attributed names that are NOT a press outlet — attribution to these is
# normal sourcing, not derivation. Lowercased containment check.
_NON_MEDIA_ATTRIBUTION = frozenset({
    "officials", "official", "authorities", "police", "army", "military",
    "government", "ministry", "witnesses", "residents", "sources", "experts",
    "analysts", "doctors", "hospital", "hospitals", "un", "united nations",
    "who", "spokesperson", "spokesman", "spokeswoman", "president",
    "prime minister", "el gobierno", "las autoridades", "la policía",
    "testigos", "fuentes",
})


def attributed_outlet(quotes: list[str]) -> str | None:
    """Most-frequent MEDIA name the quotes attribute their content to, or
    None. Normalized lowercase (matches against outlet_root by containment)."""
    from collections import Counter
    names: Counter[str] = Counter()
    for q in quotes or []:
        for rx in _ATTRIBUTION_RES:
            for m in rx.finditer(q or ""):
                name = re.sub(r"\s+", " ", m.group(1)).strip(" .,'’-").lower()
                if not name or len(name) < 3:
                    continue
                if any(nm in name or name in nm for nm in _NON_MEDIA_ATTRIBUTION):
                    continue
                names[name] += 1
    if not names:
        return None
    return names.most_common(1)[0][0]


QUOTE_OVERLAP_SAME_PRIMARY = 0.6
_MIN_QUOTE_CHARS = 40   # short quotes collide by chance


def _norm_quote(q: str) -> str:
    return re.sub(r"[^\w\s]", "", re.sub(r"\s+", " ", (q or "").lower())).strip()


def quote_overlap(quotes_a: list[str], quotes_b: list[str]) -> float:
    """Share of one article's substantial quotes contained in the other's
    (normalized substring, either direction, over the smaller set). Two
    'independent' accounts built from the same quote set = one primary."""
    na = [_norm_quote(q) for q in quotes_a or [] if len(_norm_quote(q)) >= _MIN_QUOTE_CHARS]
    nb = [_norm_quote(q) for q in quotes_b or [] if len(_norm_quote(q)) >= _MIN_QUOTE_CHARS]
    if not na or not nb:
        return 0.0
    small, big = (na, nb) if len(na) <= len(nb) else (nb, na)
    hits = sum(1 for q in small if any(q in o or o in q for o in big))
    return hits / len(small)


def same_primary_source(a: dict, b: dict) -> bool:
    """Both derive from the same named outlet, or one derives from the
    OTHER's masthead (site B attributing to Haaretz vs haaretz.com itself)."""
    da, db_ = a.get("derivative_of"), b.get("derivative_of")
    if da and db_ and da == db_:
        return True
    if da and da in (b.get("outlet_root") or ""):
        return True
    if db_ and db_ in (a.get("outlet_root") or ""):
        return True
    return False
```

Extend `_INDEPENDENCE_LABEL`:

```python
_INDEPENDENCE_LABEL = {
    "independent": "2 independent sources",
    "same_outlet": "same outlet — not independent",
    "same_wire": "2 outlets, 1 wire source",
    "same_primary_source": "2 outlets, 1 primary source (attributed)",
    "shared_quotes": "2 outlets, same underlying quotes",
}
```

Extend `articles_independent` — after the existing three checks, before `return True, "independent"`:

```python
    if same_primary_source(a, b):
        return False, "same_primary_source"
    if quote_overlap(a.get("quotes") or [], b.get("quotes") or []) \
            >= QUOTE_OVERLAP_SAME_PRIMARY:
        return False, "shared_quotes"
```

In `validate_cross` (where per-article signatures are built from `sources` + `readings` — read the current construction at article_read.py:358-403 first): when building each article's signature dict, attach the reading's quote texts and the derived attribution:

```python
        quotes = [c.get("quote") or "" for c in (reading.get("claims") or [])]
        sig["quotes"] = quotes
        sig["derivative_of"] = attributed_outlet(quotes)
```

(Adapt names to the actual local variables — the reading dicts come from `ai_readings` rows; claims carry `quote` per the F2 quote-gate. If the claim key differs (`quote` vs `exact_quote`), use the real one — check `validate_reading`.)

- [ ] **Step 4: Run the full article_read suite**

Run: `.venv/bin/python -m pytest tests/test_article_read.py tests/test_article_fetch.py -q`
Expected: PASS (pre-existing independence tests unaffected — new checks only ADD reasons for non-independence).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/article_read.py backend/tests/test_article_read.py
git commit -m "feat(corroborate-v2 R2): attribution + quote-overlap independence — G-HAARETZ fixture passes"
```

---

### Task 7: Thread through the routers (dossier + corroborate)

**Files:**
- Modify: `backend/app/routers/dossier.py` (~line 1340-1420: the `/corroborate` handler around `ind = independence(arts)` at :1360)
- Modify: `backend/app/routers/corroborate.py` (lang param — done in Task 3; verify)
- Test: `backend/tests/test_dossier_corroborate.py` (find the actual test file: `grep -rl "dossier_corroborate\|/dossier/corroborate" backend/tests`)

- [ ] **Step 1: Read the handler** (dossier.py:1330-1420) to see how `arts`, `ind`, and `pin_status` compose the per-pin payload.

- [ ] **Step 2: Write the failing test** (adapt to the file's existing fixture style — it stubs `fetch_external_depth`):

```python
def test_dossier_corroborate_counts_voices_and_carries_tiers(...):
    # supply supplied_results with ria.ru + tass.com + rt.com + cnn.com titles
    # (distinct titles so syndication clustering keeps all four)
    # assert payload pin: independent_voices == 2, status == 'unverified',
    # citations carry ownership_group ('state:ru' on ria) and tier
    # (tier label 'state' for ria, via source_tiers.tier_payload)
```

- [ ] **Step 3: Implement** — in the handler:

```python
from app.services.source_tiers import ownership_group, tier_payload
...
        ind = independence(arts, group_fn=ownership_group)
        for c in ind["citations"][:MAX_CITATIONS_PER_PIN]:
            c["credibility"] = tier_payload(c.get("outlet"))
        status, note = pin_status(
            ind["independent_voices"], search_ok,
            applicable=applicable,
            outlets=ind["independent_outlets"],
            state_collapsed=ind["state_collapsed"],
        )
```

and add `independent_voices` + `state_collapsed` to the per-pin response dict next to the existing `independent_outlets`, keeping `independent_outlets` (backward compatible). Update the payload `meta` (it documents ESTABLISHED_MIN_OUTLETS etc.) to say the bar is VOICES with the state-collapse rule — the section is glass-box by contract.

- [ ] **Step 4: Run + commit**

Run: `.venv/bin/python -m pytest tests/ -q -k "dossier and corrob"` → PASS.

```bash
git add backend/app/routers/dossier.py backend/tests/
git commit -m "feat(corroborate-v2): dossier corroborate serves voices + tiered citations"
```

---

### Task 8: Frontend — extractFigure mirror + honest labels

**Files:**
- Modify: `frontend-v2/src/lib/claimLedger.ts:95` (`extractFigure`)
- Modify: `frontend-v2/src/lib/dossierCorroboration.ts` (types: `independent_voices`, `state_collapsed`, `ownership_group`, `credibility` on citations; verdict `template_matches`/`aged`/`window_days`)
- Modify: `frontend-v2/src/components/DossierView.tsx` (render the new reasons; :432 has the shared-source copy pattern)
- Test: `frontend-v2/src/lib/claimLedger.test.ts` (or the file's existing test home — check `git grep -l "extractFigure" frontend-v2/src | grep test`)

- [ ] **Step 1: Write the failing vitest**

```ts
import { extractFigure } from './claimLedger'

it('parses dot-grouped thousands under a comma-decimal source language', () => {
  expect(extractFigure('1.700 orang tewas', 'id')).toBe(1700)
  expect(extractFigure('1.700 muertos', 'es')).toBe(1700)
  expect(extractFigure('magnitud 7,6', 'es')).toBeCloseTo(7.6)
})

it('keeps en-default behavior without a lang', () => {
  expect(extractFigure('1,700 dead')).toBe(1700)
  expect(extractFigure('magnitude 7.6')).toBeCloseTo(7.6)
  expect(extractFigure('1.700 dead')).toBeCloseTo(1.7) // unknown lang: conservative
})

it('parses unambiguous multi-group numbers in any lang', () => {
  expect(extractFigure('1.234.567 affected')).toBe(1234567)
  expect(extractFigure('1.234.567,89', 'de')).toBeCloseTo(1234567.89)
})
```

- [ ] **Step 2: Implement `extractFigure(text, sourceLang?)`** — port `_parse_figure_token` rule-for-rule (both-separators → last is decimal; multi-group → grouping; single separator + 3-digit tail → grouping in that locale's grouping char; comma-decimal langs set identical to the backend `_COMMA_DECIMAL_LANGS`). Existing call sites (claimLedger.ts:144,158 `buildClaimTable`) pass the citation's source language where the `Citation` type carries one — check the type; if it doesn't carry a lang, leave those calls 1-arg (behavior unchanged there) and note it in the commit body: the backend is the authoritative end.

- [ ] **Step 3: Render the new honesty** — in DossierView's corroboration section:
  - status note now arrives with voices/collapse wording from the backend (no change needed for the note itself — verify it renders untruncated);
  - citations with `ownership_group` starting `state:` get the existing STATE chip treatment (reuse the tier chip the receipts already use — `credibility.label`);
  - verdict rows: when `template_matches > 0` render the backend note (already in `note`); when `aged > 0` same. Cross-read findings with reason `same_primary_source`/`shared_quotes` render their `_INDEPENDENCE_LABEL` string — the label arrives from the backend; verify the component renders `finding.independence_label ?? ...` rather than hardcoding "2 independent sources" (DossierView.tsx:432 area has the switch — extend it:

```tsx
: f.kind === 'same_primary_source' ? '1 primary source (attributed) — not independent corroboration'
: f.kind === 'shared_quotes' ? 'Same underlying quotes — not independent corroboration'
```

  adapt to the actual `kind`/`reason` field name in the cross-read payload).

- [ ] **Step 4: Run + commit**

Run: `cd frontend-v2 && npx vitest run src/lib/claimLedger.test.ts && npm run build`
Expected: PASS + clean build.

```bash
git add frontend-v2/src
git commit -m "feat(corroborate-v2): frontend mirror — locale figures + voice/derivation/aged labels"
```

---

### Task 9: Gate run + deploy + artifact

**Files:**
- Create: `docs/research/corroborate-v2/2026-08-11-gate-run.md`

- [ ] **Step 1: Full backend + frontend suites**

Run: `cd backend && .venv/bin/python -m pytest tests/test_corroboration.py tests/test_article_read.py tests/test_source_tiers.py tests/ -q -k "corrob or article_read or source_tier"` then the FULL backend suite `.venv/bin/python -m pytest tests/ -q` (pre-existing exclusions per CLAUDE.md apply); `cd frontend-v2 && npx vitest run && npm run build`.
Expected: green.

- [ ] **Step 2: G-NO-REGRESIÓN**

Run: `cd backend && set -a && source /Users/pedro/AtlasLocalWorker/.env && set +a && .venv/bin/python scripts/corroborate_v2_gate.py --check`
Expected: `PASS` (drop ≤15%). **If FAIL: STOP. Do not relax any threshold. Write the per-claim delta table into the artifact doc, report, and await Pedro** — the spec pre-registers this as report-and-decide, never silent-relax.

- [ ] **Step 3: Deploy + live smoke**

Run: `./scripts/deploy-fly-api.sh`, then:

```bash
curl -s -X POST https://atlas-api-pedro.fly.dev/api/v2/corroborate \
  -H 'Content-Type: application/json' \
  -d '{"headline":"Earthquake kills dozens in coastal region","country":null}' | \
  python3 -c "import json,sys; v=json.load(sys.stdin)['verdict']; print({k:v[k] for k in ('status','corroborating','template_matches','aged','window_days')})"
```

Expected: the four new fields present; no 500.

- [ ] **Step 4: Write the gate artifact** — `docs/research/corroborate-v2/2026-08-11-gate-run.md`: the five gates, each verdict, the regression delta table, deploy receipt.

- [ ] **Step 5: Commit + push**

```bash
git add docs/research/corroborate-v2/
git commit -m "gate(corroborate-v2): five pre-registered gates run — verdicts recorded"
git push origin eclipse-dramatic-moment
```

---

## Self-review notes

- Spec coverage: R1→T1+T2+T7 · R2→T6 · R3→T5 · F1→T3+T8 · F2→T4 · G-HAARETZ→T6 · G-STATE→T2 · G-LOCALE→T3 · G-TEMPLATE→T4 · G-NO-REGRESIÓN→T0+T9 · "citations carry tier+origin"→T7 · frontend labels→T8. Budget rule (zero LLM in hot path): every addition is regex/string math. ✓
- The `similarity=0.87` in the G-TEMPLATE test encodes a REFINEMENT of spec F2 discovered at plan time: the semantic lane can produce template FPs too, and cross-script true matches share zero lexical anchors — hence the anchored-or-cross-script rule. This is a documented deviation-with-reason, recorded in the classify_relation docstring and the gate artifact.
- `independent_outlets` stays in every payload (backward compatibility); `independent_voices` is the judged number. No consumer loses a field.
