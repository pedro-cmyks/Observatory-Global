"""Post-fix re-measure of subject-geography inference (#238).

Stage 1: REPLAY — post-fix local inference over the BASELINE window's exact
receipts + the baseline's existing DeepSeek judgments (controlled delta).
Stage 2: FRESH — new prod pull, new judgments, post-fix local inference
(generalization + served-pre-fix vs local-post-fix deltas).

Fully synchronous. Writes snapshots to the versioned dir.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import unicodedata
import urllib.request

BASE = "/private/tmp/claude-501/-Users-pedro-Desktop-PEDRO-Cursos-ObservatorioGlobal/f9144380-cf02-49ba-ad81-905d8b823b00/scratchpad"
SG_BASE = os.path.join(BASE, "subjgeo")            # baseline snapshots
OUT = "/Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal/docs/research/subject-geo/snapshots-2026-07-16-postfix"
os.makedirs(OUT, exist_ok=True)

sys.path.insert(0, "/Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal/backend")
from app.services.subject_geography import infer_receipt_subject_geography  # noqa: E402

DEEPSEEK_KEY = None
for envfile in (
    "/Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal/backend/.env",
    "/Users/pedro/AtlasLocalWorker/.env",
):
    if DEEPSEEK_KEY:
        break
    try:
        for line in open(envfile):
            if line.startswith("DEEPSEEK_API_KEY="):
                DEEPSEEK_KEY = line.split("=", 1)[1].strip().strip('"')
                break
    except FileNotFoundError:
        pass
assert DEEPSEEK_KEY, "no DeepSeek key found"


def receipts_of(thread: dict) -> list[dict]:
    return [
        {"headline": ev.get("headline"), "source_name": ev.get("source")}
        for ev in (thread.get("evidence_samples") or [])
    ]


def script_counts(headlines: list[str]) -> dict:
    counts: dict[str, int] = {}
    for h in headlines[:15]:
        name = "LATIN"
        for ch in str(h or ""):
            if ch.isalpha():
                try:
                    nm = unicodedata.name(ch)
                except ValueError:
                    continue
                for s in ("CYRILLIC", "GREEK", "HANGUL", "ARABIC", "CJK", "HIRAGANA", "KATAKANA", "DEVANAGARI", "HEBREW"):
                    if nm.startswith(s):
                        name = s
                        break
                else:
                    continue
                break
        counts[name] = counts.get(name, 0) + 1
    return counts


def judge_thread(label: str, headlines: list[str]) -> dict:
    prompt = (
        "You judge the subject geography of a news thread.\n"
        "Given the thread label and a sample of receipt headlines (any language), "
        "name the country or countries the story is ABOUT — the subject of the "
        "coverage, not merely a mentioned actor or a bystander.\n"
        "Answer with JSON only, no markdown: "
        '{"subject_countries": ["XX"], "reason": "..."} '
        "where subject_countries is up to 2 ISO 3166-1 alpha-2 codes "
        "(empty list if no country is clearly the subject).\n\n"
        f"Thread label: {label}\n\nReceipt headlines:\n"
        + "\n".join(f"- {h}" for h in headlines[:15])
    )
    body = json.dumps({
        "model": "deepseek-chat",
        "temperature": 0,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(
        "https://api.deepseek.com/chat/completions",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEEPSEEK_KEY}",
        },
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = json.load(resp)
            content = data["choices"][0]["message"]["content"].strip()
            content = re.sub(r"^```(?:json)?|```$", "", content, flags=re.M).strip()
            parsed = json.loads(content)
            return {
                "subject_countries": [str(c).upper() for c in (parsed.get("subject_countries") or [])][:2],
                "reason": parsed.get("reason", ""),
            }
        except Exception as exc:  # noqa: BLE001
            if attempt == 2:
                return {"subject_countries": None, "reason": f"judge_unavailable: {exc}"}
            time.sleep(3 * (attempt + 1))
    return {"subject_countries": None, "reason": "judge_unavailable"}


def score_row(thread_id, label, local, judge, receipts):
    verified = list(local.get("verified_subject_countries") or [])
    status = local.get("status")
    j = judge.get("subject_countries")
    agree = bool(verified) and j is not None and set(verified) <= set(j)
    heads = [r["headline"] for r in receipts]
    return {
        "thread_id": thread_id,
        "label": label,
        "status": status,
        "verified": verified,
        "judge": j,
        "judge_reason": judge.get("reason"),
        "agree": agree,
        "scripts": script_counts(heads),
        "reason_codes": list(local.get("reason_codes") or []),
        "candidates": [
            {k: c.get(k) for k in (
                "country", "receipt_count", "outlet_count",
                "non_proxy_receipt_count", "non_proxy_outlet_count",
                "methods", "status", "person_proxy_suppressed")}
            for c in (local.get("candidates") or [])[:8]
        ],
        "n_receipts": len(receipts),
    }


def metrics(scored):
    judged = [r for r in scored if r["judge"] is not None]
    named = [r for r in judged if r["judge"]]
    ver = [r for r in judged if r["status"] == "verified"]
    agree = [r for r in ver if r["agree"]]
    strict = [r for r in named if r["status"] == "verified" and r["agree"]]
    lenient = [r for r in named if r["status"] == "verified"]
    dist = {}
    for r in scored:
        dist[r["status"]] = dist.get(r["status"], 0) + 1
    return {
        "n": len(scored),
        "judged": len(judged),
        "judge_named": len(named),
        "verified": len(ver),
        "precision": f"{len(agree)}/{len(ver)}" + (f" = {len(agree)/len(ver):.1%}" if ver else ""),
        "recall_strict": f"{len(strict)}/{len(named)}" + (f" = {len(strict)/len(named):.1%}" if named else ""),
        "recall_lenient": f"{len(lenient)}/{len(named)}" + (f" = {len(lenient)/len(named):.1%}" if named else ""),
        "status_distribution": dist,
    }


# ────────────────────────── Stage 1: REPLAY ──────────────────────────
print("=== Stage 1: replay baseline window with post-fix code ===")
baseline_threads = json.load(open(os.path.join(SG_BASE, "threads.json")))["threads"]
baseline_judgments = {j["thread_id"]: j["judge"] for j in json.load(open(os.path.join(SG_BASE, "judgments.json")))}
baseline_scored = {r["thread_id"]: r for r in json.load(open(os.path.join(SG_BASE, "scored.json")))}

replay_local, replay_scored = [], []
for t in baseline_threads:
    tid = t["thread_id"]
    recs = receipts_of(t)
    res = infer_receipt_subject_geography(recs)
    replay_local.append({
        "thread_id": tid, "label": t.get("label"),
        "baseline_served_status": t.get("subject_geography_status"),
        "baseline_served_subjects": t.get("subject_countries"),
        "postfix_status": res.get("status"),
        "postfix_subjects": res.get("verified_subject_countries"),
        "postfix_result": res,
    })
    row = score_row(tid, t.get("label"), res, baseline_judgments[tid], recs)
    b = baseline_scored[tid]
    row["baseline_status"] = b["status"]
    row["baseline_verified"] = b["verified"]
    row["baseline_agree"] = b["agree"]
    replay_scored.append(row)

replay_metrics = metrics(replay_scored)
print(json.dumps(replay_metrics, indent=2))
json.dump(replay_local, open(os.path.join(OUT, "replay_local_inference.json"), "w"), ensure_ascii=False, indent=1)
json.dump(replay_scored, open(os.path.join(OUT, "replay_scored.json"), "w"), ensure_ascii=False, indent=1)

print("\n--- per-thread fate (baseline -> postfix) ---")
for r in replay_scored:
    b_v, p_v = r["baseline_verified"], r["verified"]
    changed = (r["baseline_status"] != r["status"]) or (b_v != p_v)
    flag = "CHANGED" if changed else "same   "
    print(f"{flag} {r['thread_id']:22s} {r['baseline_status']:11s}{b_v} -> {r['status']:11s}{p_v}"
          f" judge={r['judge']} agree {r['baseline_agree']}->{r['agree']}")

# ────────────────────────── Stage 2: FRESH ──────────────────────────
print("\n=== Stage 2: fresh window ===")
req = urllib.request.Request("https://atlas-api-pedro.fly.dev/api/v2/threads?hours=24&limit=40")
with urllib.request.urlopen(req, timeout=60) as resp:
    fresh_payload = json.load(resp)
fresh_threads = [t for t in fresh_payload.get("threads", []) if t.get("evidence_samples")]
print(f"fresh threads with receipts: {len(fresh_threads)}")
json.dump(fresh_payload, open(os.path.join(OUT, "threads.json"), "w"), ensure_ascii=False, indent=1)

fresh_judgments, fresh_local, fresh_scored = [], [], []
for i, t in enumerate(fresh_threads):
    tid = t["thread_id"]
    recs = receipts_of(t)
    heads = [r["headline"] for r in recs]
    judge = judge_thread(t.get("label") or "", heads)
    fresh_judgments.append({"thread_id": tid, "label": t.get("label"), "judge": judge})
    res = infer_receipt_subject_geography(recs)
    fresh_local.append({
        "thread_id": tid, "label": t.get("label"),
        "served_status": t.get("subject_geography_status"),
        "served_subjects": t.get("subject_countries"),
        "local_status": res.get("status"),
        "local_subjects": res.get("verified_subject_countries"),
        "local_result": res,
    })
    fresh_scored.append(score_row(tid, t.get("label"), res, judge, recs))
    print(f"[{i+1}/{len(fresh_threads)}] {tid} served={t.get('subject_geography_status')}"
          f"{t.get('subject_countries')} local={res.get('status')}{res.get('verified_subject_countries')}"
          f" judge={judge.get('subject_countries')}")

json.dump(fresh_judgments, open(os.path.join(OUT, "judgments.json"), "w"), ensure_ascii=False, indent=1)
json.dump(fresh_local, open(os.path.join(OUT, "local_inference.json"), "w"), ensure_ascii=False, indent=1)
json.dump(fresh_scored, open(os.path.join(OUT, "scored.json"), "w"), ensure_ascii=False, indent=1)

fresh_metrics = metrics(fresh_scored)
print("\nfresh metrics:", json.dumps(fresh_metrics, indent=2))

# served (pre-fix, prod) vs local (post-fix) delta on the fresh window
deltas = [
    r for r in fresh_local
    if (r["served_status"] != r["local_status"]) or (list(r["served_subjects"] or []) != list(r["local_subjects"] or []))
]
print(f"\nserved-vs-local deltas (evidence the fixes change outcomes): {len(deltas)}/{len(fresh_local)}")
for r in deltas:
    print(f"  {r['thread_id']:22s} served {r['served_status']}{r['served_subjects']}"
          f" -> local {r['local_status']}{r['local_subjects']}")

json.dump(
    {"replay_metrics": replay_metrics, "fresh_metrics": fresh_metrics,
     "served_vs_local_delta_count": len(deltas)},
    open(os.path.join(OUT, "metrics_summary.json"), "w"), indent=2,
)
print("\nDONE")
