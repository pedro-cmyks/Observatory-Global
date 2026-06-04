# Narrative Note Synthesis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic read-only `narrative_note` to Living Thread responses and render it at the top of `ThreadFocusPanel`.

**Architecture:** Create `backend/app/services/narrative_note.py` with a pure `build_thread_narrative_note(thread)` helper. Wire it after thread dicts are assembled in `thread_intelligence.py`, then render the returned note in `ThreadFocusPanel` before dense metrics. No migration, no LLM, no external calls.

**Tech Stack:** Python 3.12 / FastAPI / pytest; React + TypeScript + Vite; CSS.

**Spec:** `docs/superpowers/specs/2026-06-04-narrative-note-synthesis-design.md`

---

## File Structure

- Create: `backend/app/services/narrative_note.py` — deterministic note builder.
- Create: `backend/tests/test_narrative_note.py` — unit tests for strong/provisional/thin notes and evidence selection.
- Modify: `backend/app/services/thread_intelligence.py` — add note to atlas, emergent, dynamic, and detail paths.
- Modify: `backend/tests/test_thread_intelligence.py` — assert atlas thread contract includes `narrative_note`.
- Modify: `backend/tests/test_threads_emergent_augment_shape.py` — shape guardrail includes `narrative_note`.
- Modify: `frontend-v2/src/components/ThreadFocusPanel.tsx` — type + render note before metrics.
- Modify: `frontend-v2/src/components/ThreadFocusPanel.css` — restrained prose styling.
- Update: `STATUS.md`, `SESSION_LOG.md`, `docs/state/PROJECT_INVENTORY.md` after verification.

---

## Task 1: Backend Note Builder (TDD)

**Files:**
- Create: `backend/app/services/narrative_note.py`
- Create: `backend/tests/test_narrative_note.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_narrative_note.py`:

```python
from app.services.narrative_note import build_thread_narrative_note


def _thread(**overrides):
    base = {
        "label": "Infrastructure and Public Services",
        "signal_count": 120,
        "changed_10h": 25,
        "source_count": 4,
        "country_count": 3,
        "top_country_names": ["Indonesia", "Brazil", "Canada"],
        "top_countries": ["ID", "BR", "CA"],
        "top_sources": ["rri.co.id", "bisnis.com", "antaranews.com"],
        "quality": {"source_flags": {}, "geo_flags": {}, "entity_flags": {}, "noise_rate": 0.08},
        "evidence_samples": [
            {"headline": "Currency pressure builds", "snippet": "Bank officials warned about public-service pressure.", "source": "rri.co.id"},
            {"headline": "Immigration document investigation widens", "snippet": None, "source": "bisnis.com"},
            {"headline": "Public-sector operations expand", "snippet": "Officials described a new regional service program.", "source": "antaranews.com"},
        ],
    }
    base.update(overrides)
    return base


def test_builds_strong_thread_note():
    note = build_thread_narrative_note(_thread())
    assert note is not None
    assert note["quality"] == "strong"
    assert note["source"] == "extractive-v1"
    assert "Infrastructure and Public Services" in note["lede"]
    assert "25-signal rise" in note["movement"]
    assert "rri.co.id" in note["evidence"]
    assert note["caveat"] is None


def test_prefers_snippet_rich_evidence_and_diversifies_sources():
    note = build_thread_narrative_note(_thread())
    assert note is not None
    assert "Bank officials warned" in note["evidence"]
    assert "Officials described" in note["evidence"]
    assert note["evidence"].count("rri.co.id") <= 1


def test_headline_only_thread_is_provisional_with_caveat():
    note = build_thread_narrative_note(_thread(evidence_samples=[
        {"headline": "Headline one", "snippet": None, "source": "gdelt-a.com"},
        {"headline": "Headline two", "snippet": None, "source": "gdelt-b.com"},
    ]))
    assert note is not None
    assert note["quality"] == "provisional"
    assert note["caveat"] is not None
    assert "headline-heavy" in note["caveat"]


def test_thin_thread_returns_thin_quality():
    note = build_thread_narrative_note(_thread(signal_count=8, source_count=1, country_count=1, top_sources=["local.test"]))
    assert note is not None
    assert note["quality"] == "thin"
    assert note["caveat"] is not None


def test_empty_thread_returns_none():
    assert build_thread_narrative_note({"label": "", "signal_count": 0, "evidence_samples": []}) is None
```

- [ ] **Step 2: Verify tests fail**

Run: `cd backend && .venv/bin/python -m pytest tests/test_narrative_note.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.narrative_note'`.

- [ ] **Step 3: Implement helper**

Create `backend/app/services/narrative_note.py` with:

```python
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


def _select_evidence(samples: list[dict[str, Any]], limit: int = 3) -> tuple[list[dict[str, str]], int]:
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
    countries = [str(v) for v in (_as_list(thread.get("top_country_names")) or _as_list(thread.get("top_countries"))) if v]
    sources = [str(v) for v in (_as_list(thread.get("top_sources")) or _as_list(thread.get("source_mix", {}).get("top_sources"))) if v]
    quality_meta = thread.get("quality") if isinstance(thread.get("quality"), dict) else {}
    noise_rate = quality_meta.get("noise_rate")
    evidence, snippet_count = _select_evidence([s for s in _as_list(thread.get("evidence_samples")) if isinstance(s, dict)])

    country_phrase = _join(countries[:3], "the visible geography")
    source_phrase = _join(sources[:3], "the visible source set")
    lede = f"{label} is moving across {country_phrase}."

    if changed_10h > 0:
        movement_delta = f"a {changed_10h:,}-signal rise"
    elif changed_10h < 0:
        movement_delta = f"a {abs(changed_10h):,}-signal drop"
    else:
        movement_delta = "flat short-term movement"
    movement = (
        f"The thread has {_format_count(signal_count)} signals, {movement_delta} in the last 10 hours, "
        f"across {country_count or len(countries) or 1} countries and {source_count or len(sources) or 1} sources."
    )

    if evidence:
        evidence_bits = [f"{item['source']}: {item['text']}" for item in evidence]
        evidence_text = "; ".join(evidence_bits)
        evidence_sentence = f"The strongest visible support comes from {source_phrase}, with evidence including {evidence_text}."
    else:
        evidence_sentence = f"The strongest visible support comes from {source_phrase}, but representative evidence samples are still sparse."

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
```

- [ ] **Step 4: Verify tests pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_narrative_note.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add backend/app/services/narrative_note.py backend/tests/test_narrative_note.py
git commit -m "feat(narrative): add extractive thread note builder"
```

---

## Task 2: Wire Notes Into Thread Contract

**Files:**
- Modify: `backend/app/services/thread_intelligence.py`
- Modify: `backend/tests/test_thread_intelligence.py`
- Modify: `backend/tests/test_threads_emergent_augment_shape.py`

- [ ] **Step 1: Write failing contract tests**

In `backend/tests/test_thread_intelligence.py`, add to `test_assemble_thread_contract`:

```python
    assert "narrative_note" in thread
    assert thread["narrative_note"] is not None
    assert thread["narrative_note"]["source"] == "extractive-v1"
```

In `backend/tests/test_threads_emergent_augment_shape.py`, add `"narrative_note"` to the required field list in `test_assemble_emergent_thread_emits_required_contract_fields`.

- [ ] **Step 2: Verify tests fail**

Run: `cd backend && .venv/bin/python -m pytest tests/test_thread_intelligence.py tests/test_threads_emergent_augment_shape.py -v`
Expected: FAIL because thread dicts do not include `narrative_note`.

- [ ] **Step 3: Wire helper**

In `backend/app/services/thread_intelligence.py`, import:

```python
from app.services.narrative_note import build_thread_narrative_note
```

Add helper:

```python
def _with_narrative_note(thread: dict[str, Any]) -> dict[str, Any]:
    thread["narrative_note"] = build_thread_narrative_note(thread)
    return thread
```

Then wrap returns from `assemble_thread`, `assemble_emergent_thread`, and the dynamic-topic assembler:

```python
    return _with_narrative_note({
        ...
    })
```

After atlas detail evidence is replaced in `fetch_thread_detail`, refresh the note:

```python
    threads[0]["evidence_samples"] = [_serialize_evidence(row) for row in evidence_rows]
    threads[0]["narrative_note"] = build_thread_narrative_note(threads[0])
    return threads[0]
```

- [ ] **Step 4: Verify tests pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_narrative_note.py tests/test_thread_intelligence.py tests/test_threads_emergent_augment_shape.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add backend/app/services/thread_intelligence.py backend/tests/test_thread_intelligence.py backend/tests/test_threads_emergent_augment_shape.py
git commit -m "feat(narrative): expose narrative_note on thread contracts"
```

---

## Task 3: Render Narrative Note In ThreadFocusPanel

**Files:**
- Modify: `frontend-v2/src/components/ThreadFocusPanel.tsx`
- Modify: `frontend-v2/src/components/ThreadFocusPanel.css`

- [ ] **Step 1: Add types and render**

In `ThreadFocusPanel.tsx`, add:

```ts
interface NarrativeNote {
    lede: string
    movement: string
    evidence: string
    caveat?: string | null
    quality: 'strong' | 'provisional' | 'thin'
    source: string
}
```

Add `narrative_note?: NarrativeNote | null` to `ThreadDetail`.

Replace the single `thread-focus-why` paragraph with:

```tsx
                    {active.narrative_note ? (
                        <section className={`thread-focus-note thread-focus-note-${active.narrative_note.quality}`}>
                            <p className="thread-focus-note-lede">{active.narrative_note.lede}</p>
                            <p>{active.narrative_note.movement}</p>
                            <p>{active.narrative_note.evidence}</p>
                            {active.narrative_note.caveat && <p className="thread-focus-note-caveat">{active.narrative_note.caveat}</p>}
                        </section>
                    ) : (
                        <p className="thread-focus-why">{active.why_now || `${formatCount(active.signal_count)} signals across ${active.country_count} countries.`}</p>
                    )}
```

- [ ] **Step 2: Add CSS**

In `ThreadFocusPanel.css`, add:

```css
.thread-focus-note {
    margin: 0 0 18px;
    padding: 14px 0 14px 14px;
    border-left: 2px solid #2dd4bf;
    color: #cbd5e1;
}

.thread-focus-note p {
    margin: 7px 0 0;
    font-size: 13px;
    line-height: 1.65;
}

.thread-focus-note p:first-child {
    margin-top: 0;
}

.thread-focus-note-lede {
    color: #f8fafc;
    font-size: 14px;
}

.thread-focus-note-caveat {
    color: #94a3b8;
}

.thread-focus-note-thin {
    border-left-color: #f59e0b;
}
```

- [ ] **Step 3: Verify build**

Run: `cd frontend-v2 && npm run build`
Expected: PASS.

- [ ] **Step 4: Commit**

Run:

```bash
git add frontend-v2/src/components/ThreadFocusPanel.tsx frontend-v2/src/components/ThreadFocusPanel.css
git commit -m "feat(narrative): render thread narrative note"
```

---

## Task 4: Final Verification And Docs

**Files:**
- Modify: `STATUS.md`
- Modify: `SESSION_LOG.md`
- Regenerate: `docs/state/PROJECT_INVENTORY.md`

- [ ] **Step 1: Run focused verification**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/test_narrative_note.py tests/test_thread_intelligence.py tests/test_threads_emergent_augment_shape.py tests/test_snippet_evidence_contract.py -v
cd frontend-v2 && npm run build
```

Expected: all pass.

- [ ] **Step 2: Live/local smoke**

Run:

```bash
curl -fsS 'http://localhost:3000/api/v2/threads?hours=24&limit=1' | backend/.venv/bin/python -m json.tool | rg -n 'narrative_note|lede|movement|evidence|caveat'
```

Expected: `narrative_note` appears with `source: extractive-v1`.

- [ ] **Step 3: Update docs**

Add a short entry to `STATUS.md` and `SESSION_LOG.md`: narrative note shipped locally, tests/build passed, backend field ready for deploy, UI renders in ThreadFocusPanel.

Run:

```bash
python3 scripts/project_inventory.py
git diff --check
```

- [ ] **Step 4: Commit and push**

Run:

```bash
git add STATUS.md SESSION_LOG.md docs/state/PROJECT_INVENTORY.md docs/superpowers/plans/2026-06-04-narrative-note-synthesis.md
git commit -m "docs(narrative): log narrative note implementation"
git push origin v3-intel-layer
```

---

## Self-Review

- Spec coverage: backend deterministic note builder, thread contract, ThreadFocusPanel UI, tests, smoke, docs.
- Out of scope preserved: no LLM, no migration, no ThemeDetail, no country notes.
- Type consistency: backend returns `lede`, `movement`, `evidence`, `caveat`, `quality`, `source`; frontend uses the same fields.
