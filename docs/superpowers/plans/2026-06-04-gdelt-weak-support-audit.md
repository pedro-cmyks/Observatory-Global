# GDELT Weak-Support Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a read-only audit that measures whether GDELT themes weakly support, contradict, or fragment active dynamic Narrative Threads, including Western/source/language bias diagnostics.

**Architecture:** Add one standalone backend script with pure scoring helpers and an async read-only query path. Tests cover the helper layer first; the script writes JSON artifacts and never mutates the database.

**Tech Stack:** Python 3.12, asyncpg, pytest, JSON artifacts under `docs/research/topic-quality/gdelt-weak-support/`.

**Spec:** `docs/superpowers/specs/2026-06-04-mvp-thread-volume-and-issue-sprint-design.md`

---

## File Structure

- Create: `backend/scripts/gdelt_weak_support_audit.py`
  - Pure helpers: domain mapping, entropy, support/contradiction scoring, bias slices, recommendation.
  - Async runner: reads active `dynamic_topics` and member/sample signals, writes JSON.
- Create: `backend/tests/test_gdelt_weak_support_audit.py`
  - Unit tests for helper behavior.
- Modify: `SESSION_LOG.md`
  - Record implementation and validation.

## Task 1: Pure Weak-Support Scoring (TDD)

**Files:**
- Create: `backend/tests/test_gdelt_weak_support_audit.py`
- Create: `backend/scripts/gdelt_weak_support_audit.py`

- [x] **Step 1: Write failing tests**

Test expected behavior:

```python
from scripts.gdelt_weak_support_audit import (
    build_thread_audit,
    infer_expected_domains,
    normalized_entropy,
    theme_domains,
)


def test_theme_domains_maps_common_gdelt_themes_to_coarse_domains():
    assert "conflict" in theme_domains("WB_2432_FRAGILITY_CONFLICT_AND_VIOLENCE")
    assert "policy" in theme_domains("USPEC_POLICY")
    assert "media_social" in theme_domains("MEDIA_SOCIAL")


def test_infer_expected_domains_from_thread_label():
    assert infer_expected_domains("Russia-Ukraine War Updates") == {"conflict", "policy"}
    assert infer_expected_domains("Social Media") == {"media_social"}


def test_normalized_entropy_is_low_for_concentrated_and_high_for_mixed():
    assert normalized_entropy({"conflict": 10}) == 0
    assert normalized_entropy({"conflict": 1, "policy": 1, "health": 1}) > 0.9


def test_build_thread_audit_reports_support_contradiction_and_bias_slices():
    report = build_thread_audit(
        {
            "thread_id": "dynamic-topic-10",
            "label": "Russia-Ukraine War Updates",
            "signal_count": 100,
            "country_count": 3,
            "source_count": 4,
            "noise_rate": 0.1,
        },
        [
            {
                "signal_id": 1,
                "headline": "Ukraine talks continue after strikes",
                "themes": ["WB_2432_FRAGILITY_CONFLICT_AND_VIOLENCE", "USPEC_POLICY"],
                "country_code": "UA",
                "source_lang": "en",
                "source_family": "api",
                "source_name": "example.com",
            },
            {
                "signal_id": 2,
                "headline": "Celebrity post trends online",
                "themes": ["MEDIA_SOCIAL"],
                "country_code": "US",
                "source_lang": "en",
                "source_family": "social",
                "source_name": "reddit/r/worldnews",
            },
        ],
    )

    assert report["expected_domains"] == ["conflict", "policy"]
    assert report["metrics"]["weak_support_pct"] == 0.5
    assert report["metrics"]["weak_contradiction_pct"] == 0.5
    assert report["bias"]["by_source_lang"]["en"]["rows"] == 2
    assert report["examples"]["supported"][0]["signal_id"] == 1
    assert report["examples"]["contradicted"][0]["signal_id"] == 2
```

- [x] **Step 2: Run test to verify failure**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/test_gdelt_weak_support_audit.py -v
```

Expected: fail with `ModuleNotFoundError` for `scripts.gdelt_weak_support_audit`.

- [x] **Step 3: Implement minimal helper layer**

Create the script with:

- coarse GDELT theme domain mapping by prefix/keyword;
- label keyword inference;
- normalized Shannon entropy;
- per-row support/contradiction classification;
- bias slices by language, country group, and source family;
- read-only report object.

- [x] **Step 4: Run test to verify pass**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/test_gdelt_weak_support_audit.py -v
```

Expected: pass.

## Task 2: Read-Only Runner And Artifact

**Files:**
- Modify: `backend/scripts/gdelt_weak_support_audit.py`
- Modify: `SESSION_LOG.md`

- [x] **Step 1: Add async SQL runner**

Query active `dynamic_topics`, collect member `sample_signal_ids`, join
`signals_v2`, and call `build_thread_audit`.

- [x] **Step 2: Add CLI**

Arguments:

```bash
--hours 24
--limit 20
--output docs/research/topic-quality/gdelt-weak-support/2026-06-04-live.json
```

The CLI should create the parent directory and write pretty JSON.

- [x] **Step 3: Focused validation**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/test_gdelt_weak_support_audit.py -v
cd ..
python3 backend/scripts/gdelt_weak_support_audit.py --hours 24 --limit 10 --output docs/research/topic-quality/gdelt-weak-support/2026-06-04-live.json
```

Expected:

- tests pass;
- JSON artifact exists;
- report includes `schema_version=atlas-gdelt-weak-support-v1`;
- no database writes.

- [x] **Step 4: Document validation**

Update `SESSION_LOG.md` with the report path and a short summary.

## Task 3: Conservative Recall Pilot

**Files:**
- Create: `backend/scripts/gdelt_weak_recall_pilot.py`
- Create: `backend/tests/test_gdelt_weak_recall_pilot.py`
- Create: `docs/research/topic-quality/gdelt-weak-support/2026-06-04-recall-pilot.json`
- Modify: `SESSION_LOG.md`

- [x] **Step 1: Write failing tests**

Covered:

- selecting expansion themes only when their mapped domains overlap expected
  thread domains;
- rejecting over-broad expansion themes (`GENERAL_*`, `TAX_FNCACT_*`,
  language metadata, generic CrisisLex safety);
- deriving conservative label anchor terms and skipping generic labels;
- excluding current sample ids from added candidates.

- [x] **Step 2: Run tests to verify failure**

Initial run failed with `ModuleNotFoundError`. Follow-up RED tests caught two
real issues: `UNGP_*` was too broad and generic GDELT themes expanded noisy
candidates.

- [x] **Step 3: Implement read-only pilot**

`gdelt_weak_recall_pilot.py` now:

- reuses the weak-support audit;
- selects compatible, non-generic GDELT themes;
- requires label anchor terms such as `russia`/`ukraine`;
- queries candidate signals read-only;
- writes a review sample artifact without product promotion.

- [x] **Step 4: Validate live**

Run:

```bash
backend/.venv/bin/python backend/scripts/gdelt_weak_recall_pilot.py \
  --hours 24 \
  --limit 8 \
  --candidate-limit 500 \
  --review-limit 12 \
  --output docs/research/topic-quality/gdelt-weak-support/2026-06-04-recall-pilot.json
```

Expected: JSON artifact with `schema_version=atlas-gdelt-weak-recall-pilot-v1`.
Observed: `Russia-Ukraine War Updates` recovered 33 conservative candidates;
generic/noisy threads did not expand.
