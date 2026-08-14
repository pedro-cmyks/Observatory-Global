"""The double check: ask the same question both ways, fail when they diverge.

Spec: `docs/superpowers/specs/2026-08-14-atlas-query-protocol-design.md`
("La mitad que hace la idea grande"). Pedro's framing: *"eso tendría que ser lo
mismo que yo encontraría buscando de manera visual — como un doble cheque."*

A protocol that only ADDS a door is a convenience. A protocol that can be
checked against the door already shipped is an INSTRUMENT: if the two paths
disagree, one of them is wrong and the system now says which. This script is
that instrument.

Both paths go over HTTP against the SAME deployment, so what is compared is
what is actually served — not two code paths in one process that could agree
with each other and both be wrong.

SEEDED WITH THE FOUR DEFECTS OF 2026-08-14 (investigation
`docs/research/investigations/2026-08-14-colombia-ruta-*`), so it demonstrably
catches them if they ever regress:

  D1  the source count topped out at 20 while the sample carried 36 domains
  D2  "18 · last 7d" served against 323 lifetime — a snapshot number wearing a
      window label
  D3  one story served as one when the base holds nine live identities
  D4  a VE chip on a Colombian story

CONTROLS (C1, C2). Two questions the two paths answer with the SAME function by
construction (`voice_mix`). They MUST pass. If a control fails, the harness is
broken and every other verdict in the run is suspect — the same role the
negative controls play in the gold query set.

VERDICTS
  PASS      the two paths agree, or they differ and the serving side DECLARES
            the difference (a declared sample is not a lie)
  FAIL      they disagree and nothing on the serving side says so
  SKIP      a precondition was missing (no subject topic, a lane degraded);
            never silently counted as a pass

EXIT STATUS
  0   every check that ran, agreed
  1   at least one FAIL — the two paths disagree
  2   NOTHING was measured (all SKIP)

The 2 is deliberate and is the script applying its own rule to itself: an
all-skip run exiting 0 would be an unmeasured run reported as a clean one,
which is the precise failure mode this whole protocol exists to end. It
happens for real — six protocol calls against a 20/300s bucket means two
back-to-back runs throttle, and the second one measures nothing.

Nothing is wired to cron here — that is Pedro's call.

Run:
    python scripts/query_parity_check.py                      # prod
    python scripts/query_parity_check.py --base-url http://localhost:8000
    python scripts/query_parity_check.py --json
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from typing import Any, Optional

DEFAULT_BASE = "https://atlas-api-pedro.fly.dev"
TIMEOUT_S = 60

PASS, FAIL, SKIP = "PASS", "FAIL", "SKIP"

# The event the investigation used. Overridable — the point is the mechanism,
# not this story, and these identities will age out.
DEFAULT_TERMS = ["earthquake", "terremoto"]
DEFAULT_COUNTRY = "CO"

# D3's bar: the base holding this many live identities for one event while the
# product serves one story is the fragmentation defect, not a ranking choice.
FRAGMENTATION_BAR = 3


# ------------------------------------------------------------------- http

def _post(base: str, path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        f"{base}{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as res:
        return json.loads(res.read().decode())


def _get(base: str, path: str) -> dict:
    with urllib.request.urlopen(f"{base}{path}", timeout=TIMEOUT_S) as res:
        return json.loads(res.read().decode())


def _ask(base: str, verb: str, args: dict) -> dict:
    """Run one verb and return its result block (or a synthetic degraded one)."""
    try:
        out = _post(base, "/api/v3/query", {"ask": [{verb: args}]})
    except urllib.error.HTTPError as exc:
        return {"status": "degraded", "reason": f"http_{exc.code}",
                "detail": exc.read().decode()[:300]}
    except Exception as exc:  # noqa: BLE001
        return {"status": "degraded", "reason": "transport", "detail": str(exc)[:300]}
    results = out.get("results") or []
    return results[0] if results else {"status": "degraded", "reason": "no_result"}


# ------------------------------------------------------------------ checks

class Ledger:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def add(self, *, check: str, defect: str, question: str, verdict: str,
            protocol: Any, serving: Any, note: str) -> None:
        self.rows.append({
            "check": check, "defect": defect, "question": question,
            "verdict": verdict, "protocol": protocol, "serving": serving,
            "note": note,
        })

    @property
    def failures(self) -> list[dict]:
        return [r for r in self.rows if r["verdict"] == FAIL]

    @property
    def control_failures(self) -> list[dict]:
        return [r for r in self.rows
                if r["verdict"] == FAIL and r["check"].startswith("C")]


def _subject_topic(base: str, terms: list[str], country: Optional[str],
                   ledger: Ledger) -> tuple[Optional[str], dict]:
    """D3 and the subject discovery, in one call.

    Deliberately DISCOVERS the topic rather than hardcoding dt-12927: an id
    frozen into a check rots, and a rotted check is worse than no check.
    """
    result = _ask(base, "identities_covering",
                  {"terms": terms, "country": country, "window_days": 7})
    if result.get("status") != "live":
        ledger.add(check="D3", defect="one story served, nine in the base",
                   question="how many live identities cover this event?",
                   verdict=SKIP, protocol=result.get("reason"), serving=None,
                   note="the protocol lane did not answer; nothing compared")
        return None, result

    data = result["data"]
    identities = data["identities"]
    n_identities = data["summary"]["identity_count"]

    # The sharpest possible form of the question. Raw identity count over broad
    # terms is not it: "earthquake" legitimately spans Colombia, Japan and
    # Naples, so a big number there is not by itself a defect. Two identities
    # carrying the SAME LABEL are unambiguously one story fragmented — no
    # interpretation required. So D3 measures the largest duplicate-label group
    # and asks how many of its fragments the product surfaces.
    duplicates = data["summary"]["duplicate_labels"]
    if not duplicates:
        ledger.add(check="D3", defect="one story served, nine in the base",
                   question="does one story live in several identities?",
                   verdict=PASS, protocol=0, serving=None,
                   note=f"no two of the {n_identities} matched identities share a "
                        f"label — no fragmentation detectable by this test")
        return _pick_topic(identities), result

    groups = sorted(
        ((lab, [i for i in identities if (i.get("label") or "").lower() == lab])
         for lab in duplicates),
        key=lambda kv: -len(kv[1]))
    label, fragments = groups[0]

    try:
        served = _get(base, "/api/v2/threads?hours=168&limit=40")
        threads = served.get("threads") or served.get("data") or []
        matched = [t for t in threads
                   if (str(t.get("label") or "").strip().lower() == label)]
    except Exception as exc:  # noqa: BLE001
        ledger.add(check="D3", defect="one story served, nine in the base",
                   question="does one story live in several identities?",
                   verdict=SKIP, protocol=len(fragments), serving=str(exc)[:200],
                   note="the serving list did not answer")
        return _pick_topic(identities), result

    verdict = PASS
    note = (f"'{label}' exists as {len(fragments)} identities; the thread list "
            f"surfaces {len(matched)}")
    if len(fragments) >= 2 and len(matched) <= 1:
        verdict = FAIL
        ids = [f["topic_id"] for f in fragments]
        note = (f"THE 2026-08-14 DEFECT: the label '{label}' is carried by "
                f"{len(fragments)} separate live identities ({', '.join(ids)}) "
                f"and the product serves {len(matched)}. A reader cannot learn "
                f"the other {len(fragments) - len(matched)} exist. Across all "
                f"{n_identities} matched identities there are "
                f"{len(duplicates)} such duplicated labels: {duplicates}")

    ledger.add(check="D3", defect="one story served, nine in the base",
               question="does one story live in several identities?",
               verdict=verdict, protocol=len(fragments), serving=len(matched),
               note=note)
    return _pick_topic(identities), result


def _pick_topic(identities: list[dict]) -> Optional[str]:
    """The largest REAL story identity with measurable members.

    Must be `dynamic_identity`: an `atlas_category` is a category lens, not a
    story, and an `orphan_members` id has no identity row for the serving path
    to resolve — picking either makes every downstream check SKIP on a
    precondition rather than measure anything. (Both mistakes happened on the
    first local run: the picker chose `dynamic-topic-11581`, an orphan, and D1
    / D2 / D4 all came back empty-handed.)

    Must also be ACTIVE. `_DYNAMIC_TOPIC_DETAIL_SQL` filters
    `dt.state = 'active'`, so the theme door serves nothing at all for a
    candidate — comparing against it would report the lifecycle as a
    divergence. (Second mistake caught on the local run: the picker chose
    `dynamic-topic-6692`, a candidate, and D1/D2/D4 compared against an empty
    payload. Worth noting in passing that the protocol CAN see candidates the
    theme door cannot; that is a real asymmetry, but it is by design and not
    what these checks are guarding.)
    """
    real = [i for i in identities if i.get("kind") == "dynamic_identity"]
    active = [i for i in real if i.get("state") == "active"]
    active_with_members = [i for i in active if i.get("matched_members")]
    for pool in (active_with_members, active, real):
        if pool:
            return pool[0]["topic_id"]
    return None


def _check_sources(base: str, topic_id: str, geo: dict, ledger: Ledger) -> None:
    """D1 — is the served source COUNT a count, or a display slice?"""
    try:
        theme = _get(base, f"/api/v2/theme/{topic_id}")
    except Exception as exc:  # noqa: BLE001
        ledger.add(check="D1", defect="source count capped at 20",
                   question="how many distinct sources does this topic have?",
                   verdict=SKIP, protocol=None, serving=str(exc)[:200],
                   note="theme detail did not answer")
        return

    served_count = theme.get("sourceCount")
    top_sources = theme.get("topSources") or []
    basis = theme.get("sourceCountBasis")
    sample_size = theme.get("sourceSampleSize")
    true_count = geo.get("data", {}).get("distinct_sources")

    if served_count is None or true_count is None:
        ledger.add(check="D1", defect="source count capped at 20",
                   question="how many distinct sources does this topic have?",
                   verdict=SKIP, protocol=true_count, serving=served_count,
                   note="one side served no count")
        return

    verdict, notes = PASS, []
    # THE regression guard. A count equal to a display slice sitting exactly on
    # its cap is the "20 Sources over 36 domains" shape, whatever else is true.
    if len(top_sources) >= 20 and served_count == len(top_sources):
        verdict = FAIL
        notes.append(
            f"THE 2026-08-14 DEFECT: sourceCount ({served_count}) equals the "
            f"length of the topSources display slice, which is sitting on its "
            f"20-item cap — a cap being served as a total")

    # The two numbers count over DIFFERENT populations: the theme door resolves
    # `sample_signal_ids` across every snapshot, the protocol counts distinct
    # `source_name` over current `topic_members`. So a difference is expected —
    # but it must never be reported as agreement, and the serving side must
    # DECLARE its base. Saying "counts agree" over a 34-vs-142 gap would be the
    # exact failure this script exists to catch, committed by the script.
    if served_count != true_count:
        detail = (f"serving {served_count} vs substrate {true_count} — different "
                  f"populations: serving counts distinct domains over its "
                  f"receipt sample")
        if basis:
            detail += (f", DECLARED as '{basis}'"
                       + (f" over {sample_size} receipts" if sample_size else ""))
            detail += ("; protocol counts distinct source_name over current "
                       "topic_members evidence. A declared difference of base, "
                       "not a divergence of fact")
            notes.append(detail)
        else:
            verdict = FAIL
            notes.append(detail + ", and declares NO basis for the difference")
    else:
        notes.append(f"both paths count {served_count} distinct sources")

    ledger.add(check="D1", defect="source count capped at 20",
               question="how many distinct sources does this topic have?",
               verdict=verdict, protocol=true_count, serving=served_count,
               note="; ".join(notes))


def _check_count_basis(base: str, topic_id: str, geo: dict, ledger: Ledger) -> None:
    """D2 — '18 · last 7d': a snapshot number wearing a window label."""
    try:
        theme = _get(base, f"/api/v2/theme/{topic_id}")
    except Exception as exc:  # noqa: BLE001
        ledger.add(check="D2", defect="'18 · last 7d' vs 323 lifetime",
                   question="how many signals does this topic have, over what window?",
                   verdict=SKIP, protocol=None, serving=str(exc)[:200],
                   note="theme detail did not answer")
        return

    current = theme.get("currentTotal")
    current_basis = theme.get("currentBasis")
    lifetime = theme.get("total")
    count_basis = theme.get("countBasis")
    window_hours = theme.get("countWindowHours")
    measured_receipts = geo.get("data", {}).get("members_recorded")

    verdict, notes = PASS, []
    # The cure for D2 was making each number carry its basis. If a basis field
    # ever goes missing, the label is unanchored again and the defect is back.
    if not current_basis:
        verdict = FAIL
        notes.append(f"currentTotal ({current}) is served with a window label of "
                     f"{window_hours}h and NO currentBasis — this is the shape "
                     f"that produced '18 · last 7d'")
    if not count_basis:
        verdict = FAIL
        notes.append(f"total ({lifetime}) is served with no countBasis")
    if current_basis and count_basis:
        notes.append(
            f"served {current} as '{current_basis}' over a {window_hours}h "
            f"clustering window and {lifetime} as '{count_basis}'; the substrate "
            f"records {measured_receipts} evidence members. Three different "
            f"questions, three declared bases")

    ledger.add(check="D2", defect="'18 · last 7d' vs 323 lifetime",
               question="how many signals does this topic have, over what window?",
               verdict=verdict,
               protocol={"evidence_members": measured_receipts},
               serving={"currentTotal": current, "currentBasis": current_basis,
                        "total": lifetime, "countBasis": count_basis,
                        "countWindowHours": window_hours},
               note="; ".join(notes))


def _check_country(base: str, topic_id: str, geo: dict, ledger: Ledger) -> None:
    """D4 — the VE chip: does the served country match the receipts?"""
    subject = geo.get("data", {}).get("subject_countries") or []
    if not subject:
        ledger.add(check="D4", defect="VE chip on a Colombian story",
                   question="which country do this topic's receipts come from?",
                   verdict=SKIP, protocol=None, serving=None,
                   note="the topic has no resolvable receipts to compare against")
        return
    measured_top = subject[0]["cc"]

    try:
        theme = _get(base, f"/api/v2/theme/{topic_id}")
    except Exception as exc:  # noqa: BLE001
        ledger.add(check="D4", defect="VE chip on a Colombian story",
                   question="which country do this topic's receipts come from?",
                   verdict=SKIP, protocol=measured_top, serving=str(exc)[:200],
                   note="theme detail did not answer")
        return

    breakdown = theme.get("countryBreakdown") or []
    served_top = breakdown[0].get("code") if breakdown else None

    verdict, note = PASS, (
        f"both paths lead with {measured_top} "
        f"({subject[0]['n']} of {sum(s['n'] for s in subject)} receipts)")
    if served_top and served_top != measured_top:
        verdict = FAIL
        measured_ccs = {s["cc"] for s in subject}
        absent = (f"{served_top} does not appear among this topic's receipts AT "
                  f"ALL") if served_top not in measured_ccs else (
                      f"{served_top} is present but not the leader")
        note = (f"THE 2026-08-14 DEFECT SHAPE: the product leads this topic with "
                f"{served_top} while its receipts lead with {measured_top} "
                f"({subject[0]['pct']:.0%} of them) — {absent}. Full measured "
                f"mix: {[(s['cc'], s['n']) for s in subject[:5]]}")
    elif served_top is None:
        verdict = SKIP
        note = "serving returned no country breakdown to compare"

    ledger.add(check="D4", defect="VE chip on a Colombian story",
               question="which country do this topic's receipts come from?",
               verdict=verdict, protocol=measured_top, serving=served_top,
               note=note)


def _control_topic_voice(base: str, topic_id: str, ledger: Ledger) -> None:
    """C1 — same aggregation function on both sides. MUST pass."""
    result = _ask(base, "voice_mix", {"topic_id": topic_id, "window_days": 7})
    if result.get("status") != "live":
        ledger.add(check="C1", defect="(control)",
                   question="who speaks inside this topic?", verdict=SKIP,
                   protocol=result.get("reason"), serving=None,
                   note="protocol lane degraded")
        return
    try:
        served = _get(base, f"/api/v2/topic/{topic_id}/voice")
    except Exception as exc:  # noqa: BLE001
        ledger.add(check="C1", defect="(control)",
                   question="who speaks inside this topic?", verdict=SKIP,
                   protocol=None, serving=str(exc)[:200], note="serving did not answer")
        return

    p = result["data"]
    s = served.get("voice") or served
    fields = ("voices_total", "language_unknown", "origin_unattributed",
              "subject_country")
    diffs = {f: (p.get(f), s.get(f)) for f in fields if p.get(f) != s.get(f)}
    verdict = FAIL if diffs else PASS
    note = ("control diverged — the harness or the shared function is broken, "
            f"treat every other verdict in this run as suspect: {diffs}") if diffs \
        else "both paths run the same aggregation and agree field for field"
    ledger.add(check="C1", defect="(control)",
               question="who speaks inside this topic?", verdict=verdict,
               protocol={f: p.get(f) for f in fields},
               serving={f: s.get(f) for f in fields}, note=note)


def _control_country_voice(base: str, country: str, ledger: Ledger) -> None:
    """C2 — the country Voice Mix, same function both sides. MUST pass.

    24h, not 168h, deliberately: the country aggregation is bounded at 2500ms
    per statement and a 7-day CO window measures ~2.1-2.7s against it, so a
    168h control SKIPs about half the time on load. A control that flickers
    teaches nothing — this one has to be reliably measurable to be worth
    running.
    """
    result = _ask(base, "voice_mix", {"country": country, "window_hours": 24})
    if result.get("status") != "live":
        ledger.add(check="C2", defect="(control)",
                   question=f"what is {country}'s voice mix?", verdict=SKIP,
                   protocol=result.get("reason"), serving=None,
                   note="protocol lane degraded")
        return
    try:
        served = _get(base, f"/api/v2/voice-mix?hours=24&country={country}")
    except Exception as exc:  # noqa: BLE001
        ledger.add(check="C2", defect="(control)",
                   question=f"what is {country}'s voice mix?", verdict=SKIP,
                   protocol=None, serving=str(exc)[:200], note="serving did not answer")
        return

    p, s = result["data"], served
    fields = ("total_signals", "distinct_sources", "voice_entropy",
              "diversity_score", "language_known")
    # Both sides are live aggregates over a moving corpus; a re-ingest between
    # the two calls moves the totals honestly. Compare within a tolerance and
    # say so, rather than reporting ingest as a defect.
    diffs = {}
    for f in fields:
        a, b = p.get(f), s.get(f)
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            if b and abs(a - b) / max(abs(b), 1) > 0.02:
                diffs[f] = (a, b)
        elif a != b:
            diffs[f] = (a, b)
    verdict = FAIL if diffs else PASS
    note = (f"control diverged beyond the 2% ingest tolerance: {diffs}") if diffs \
        else "both paths agree within the 2% tolerance for corpus movement"
    ledger.add(check="C2", defect="(control)",
               question=f"what is {country}'s voice mix?", verdict=verdict,
               protocol={f: p.get(f) for f in fields},
               serving={f: s.get(f) for f in fields}, note=note)


# -------------------------------------------------------------------- main

def run(base: str, terms: list[str], country: Optional[str],
        topic_override: Optional[str]) -> tuple[Ledger, Optional[str]]:
    """-> (ledger, subject topic).

    The subject is DISCOVERED per run, so it drifts as the corpus moves and two
    runs are not automatically comparable. That is the right trade for a live
    instrument (a frozen id rots), but it means the run must NAME the topic it
    judged or its verdicts cannot be read later. Pass --topic-id to pin one.
    """
    ledger = Ledger()

    topic_id, _ = _subject_topic(base, terms, country, ledger)
    if topic_override:
        topic_id = topic_override

    if not topic_id:
        for check, defect in (("D1", "source count capped at 20"),
                              ("D2", "'18 · last 7d' vs 323 lifetime"),
                              ("D4", "VE chip on a Colombian story"),
                              ("C1", "(control)")):
            ledger.add(check=check, defect=defect,
                       question="(needs a subject topic)", verdict=SKIP,
                       protocol=None, serving=None,
                       note="no subject topic was discovered for these terms")
        _control_country_voice(base, country or DEFAULT_COUNTRY, ledger)
        return ledger, None

    geo = _ask(base, "receipt_geography", {"topic_id": topic_id})
    if geo.get("status") != "live":
        for check, defect in (("D1", "source count capped at 20"),
                              ("D2", "'18 · last 7d' vs 323 lifetime"),
                              ("D4", "VE chip on a Colombian story")):
            ledger.add(check=check, defect=defect, question="(needs receipt geography)",
                       verdict=SKIP, protocol=geo.get("reason"), serving=None,
                       note="the receipt_geography lane did not answer")
    else:
        _check_sources(base, topic_id, geo, ledger)
        _check_count_basis(base, topic_id, geo, ledger)
        _check_country(base, topic_id, geo, ledger)

    _control_topic_voice(base, topic_id, ledger)
    _control_country_voice(base, country or DEFAULT_COUNTRY, ledger)
    return ledger, topic_id


def _render(ledger: Ledger, base: str, topic_hint: Optional[str]) -> str:
    lines = [
        "ATLAS QUERY PARITY CHECK",
        f"  target      {base}",
        f"  subject     {topic_hint or '(none discovered)'}",
        "",
    ]
    for row in ledger.rows:
        lines.append(f"[{row['verdict']:4}] {row['check']}  {row['question']}")
        lines.append(f"         defect guarded : {row['defect']}")
        lines.append(f"         protocol       : {row['protocol']}")
        lines.append(f"         serving        : {row['serving']}")
        if row["note"]:
            lines.append(f"         {row['note']}")
        lines.append("")

    passed = sum(1 for r in ledger.rows if r["verdict"] == PASS)
    failed = len(ledger.failures)
    skipped = sum(1 for r in ledger.rows if r["verdict"] == SKIP)
    lines.append(f"{passed} pass / {failed} FAIL / {skipped} skip")
    if not passed and not failed:
        lines.append(
            "NOTHING WAS MEASURED — this run is not a pass. Most often the "
            "20/300s query bucket from a previous run; wait 5 minutes.")
    if ledger.control_failures:
        lines.append(
            "CONTROL FAILED — the harness itself is suspect; do not read the "
            "other verdicts as findings.")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base-url", default=DEFAULT_BASE)
    ap.add_argument("--terms", nargs="*", default=DEFAULT_TERMS)
    ap.add_argument("--country", default=DEFAULT_COUNTRY)
    ap.add_argument("--topic-id", default=None,
                    help="skip discovery and check this topic")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    country = args.country or None
    ledger, subject = run(args.base_url, list(args.terms), country, args.topic_id)
    pinned = " (pinned)" if args.topic_id else " (discovered)"

    if args.json:
        print(json.dumps({"base_url": args.base_url, "terms": args.terms,
                          "country": country, "subject_topic": subject,
                          "subject_pinned": bool(args.topic_id),
                          "rows": ledger.rows}, indent=2, default=str))
    else:
        print(_render(ledger, args.base_url,
                      f"{subject}{pinned}" if subject else None))

    if ledger.failures:
        return 1
    measured = any(r["verdict"] != SKIP for r in ledger.rows)
    return 0 if measured else 2


if __name__ == "__main__":
    sys.exit(main())
