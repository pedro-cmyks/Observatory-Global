"""Remeasure subject-geography inference WITH NER places (#238 D, 2026-07-16).

The heavy half (nlp_places backfill over the exact receipt ids the front page
serves — see backfill_places.py / backfill_ledger.json) is done. This script:

1. Reuses threads_fresh.json (verified live-identical at run time: same 31
   thread ids, receipts byte-identical on spot-checked threads).
2. Fetches nlp_places for every receipt id (DB is the source of truth — the
   ledger only covers rows that lacked places at backfill time).
3. Runs infer_receipt_subject_geography twice over the same receipts:
   WITHOUT places (= post-fix + dominance-cap code as committed — should
   reproduce the cap-sim 86.7%/41.9%) and WITH places (the measurement).
4. Judges each thread once (deepseek-chat, temp 0, same prompt as the
   baseline artifact) AND replays against the baseline window's judgments
   (versioned in ../snapshots-2026-07-16-postfix/baseline-judgments.json)
   so the before/after row is judge-controlled.
5. Writes judgments.json / local_inference.json / scored*.json next to the
   ledger.

Run: cd backend && .venv/bin/python <this file>   (needs asyncpg + DeepSeek key)
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import time
import unicodedata
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
POSTFIX = os.path.join(os.path.dirname(HERE), "snapshots-2026-07-16-postfix")

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


def worker_env(key: str) -> str | None:
    for line in open("/Users/pedro/AtlasLocalWorker/.env"):
        if line.startswith(key + "="):
            return line.split("=", 1)[1].strip().strip('"')
    return None


async def fetch_places(ids: list[int]) -> dict[int, list[str]]:
    import asyncpg
    conn = await asyncpg.connect(worker_env("DATABASE_URL"), statement_cache_size=0)
    rows = await conn.fetch(
        "SELECT id, nlp_places FROM signals_v2 WHERE id = ANY($1::bigint[])",
        ids,
    )
    await conn.close()
    out: dict[int, list[str]] = {}
    for r in rows:
        raw = r["nlp_places"]
        if raw is None:
            continue
        places = json.loads(raw) if isinstance(raw, str) else raw
        if isinstance(places, list):
            out[int(r["id"])] = [str(p) for p in places]
    return out


def receipts_of(thread: dict, places_by_id: dict[int, list[str]] | None) -> list[dict]:
    recs = []
    for ev in thread.get("evidence_samples") or []:
        row = {
            "id": ev.get("id"),
            "headline": ev.get("headline"),
            "source_name": ev.get("source"),
        }
        if places_by_id is not None:
            row["places"] = places_by_id.get(int(ev.get("id") or 0), [])
        recs.append(row)
    return recs


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
                for s in ("CYRILLIC", "GREEK", "HANGUL", "ARABIC", "CJK",
                          "HIRAGANA", "KATAKANA", "DEVANAGARI", "HEBREW"):
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
                "methods", "status", "person_proxy_suppressed",
                "dominance_capped")}
            for c in (local.get("candidates") or [])[:10]
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


def main() -> None:
    threads = [
        t for t in json.load(open(os.path.join(HERE, "threads_fresh.json")))["threads"]
        if t.get("evidence_samples")
    ]
    print(f"threads: {len(threads)}")

    all_ids = sorted({
        int(e["id"]) for t in threads for e in t["evidence_samples"]
    })
    places_by_id = asyncio.run(fetch_places(all_ids))
    with_places = sum(1 for v in places_by_id.values() if v)
    print(f"receipt ids: {len(all_ids)} · rows w/ nlp_places non-null: {len(places_by_id)} · >=1 place: {with_places}")

    baseline_judgments = {
        j["thread_id"]: j["judge"]
        for j in json.load(open(os.path.join(POSTFIX, "baseline-judgments.json")))
    }

    fresh_judgments = []
    local_rows = []
    scored_fresh, scored_baseline = [], []
    scored_noplaces_baseline = []
    for i, t in enumerate(threads):
        tid = t["thread_id"]
        recs_no = receipts_of(t, None)
        recs_pl = receipts_of(t, places_by_id)
        res_no = infer_receipt_subject_geography(recs_no)
        res_pl = infer_receipt_subject_geography(recs_pl)
        heads = [r["headline"] for r in recs_no]
        judge = judge_thread(t.get("label") or "", heads)
        fresh_judgments.append({"thread_id": tid, "label": t.get("label"), "judge": judge})
        local_rows.append({
            "thread_id": tid, "label": t.get("label"),
            "served_status": t.get("subject_geography_status"),
            "served_subjects": t.get("subject_countries"),
            "noplaces_status": res_no.get("status"),
            "noplaces_subjects": res_no.get("verified_subject_countries"),
            "places_status": res_pl.get("status"),
            "places_subjects": res_pl.get("verified_subject_countries"),
            "places_result": res_pl,
            "noplaces_result": res_no,
            "n_receipts_with_places": sum(1 for r in recs_pl if r.get("places")),
        })
        scored_fresh.append(score_row(tid, t.get("label"), res_pl, judge, recs_pl))
        scored_baseline.append(score_row(tid, t.get("label"), res_pl, baseline_judgments[tid], recs_pl))
        scored_noplaces_baseline.append(score_row(tid, t.get("label"), res_no, baseline_judgments[tid], recs_no))
        print(f"[{i+1}/{len(threads)}] {tid} noplaces={res_no['status']}{res_no['verified_subject_countries']}"
              f" places={res_pl['status']}{res_pl['verified_subject_countries']}"
              f" judge={judge.get('subject_countries')} bl_judge={baseline_judgments[tid].get('subject_countries')}")

    json.dump(fresh_judgments, open(os.path.join(HERE, "judgments.json"), "w"), ensure_ascii=False, indent=1)
    json.dump(local_rows, open(os.path.join(HERE, "local_inference.json"), "w"), ensure_ascii=False, indent=1)
    json.dump(scored_fresh, open(os.path.join(HERE, "scored_fresh_judge.json"), "w"), ensure_ascii=False, indent=1)
    json.dump(scored_baseline, open(os.path.join(HERE, "scored.json"), "w"), ensure_ascii=False, indent=1)
    json.dump(scored_noplaces_baseline, open(os.path.join(HERE, "scored_noplaces_baseline_judge.json"), "w"), ensure_ascii=False, indent=1)

    summary = {
        "noplaces_vs_baseline_judge (should reproduce cap-sim)": metrics(scored_noplaces_baseline),
        "places_vs_baseline_judge (measurement of record)": metrics(scored_baseline),
        "places_vs_fresh_judge (secondary)": metrics(scored_fresh),
        "receipt_ids": len(all_ids),
        "rows_with_places_nonnull": len(places_by_id),
        "rows_with_ge1_place": with_places,
    }
    json.dump(summary, open(os.path.join(HERE, "metrics_summary.json"), "w"), indent=2)
    print(json.dumps(summary, indent=2))

    print("\n--- threads whose outcome CHANGED with places (vs no-places) ---")
    for r in local_rows:
        if (r["noplaces_status"] != r["places_status"]) or (r["noplaces_subjects"] != r["places_subjects"]):
            print(f"  {r['thread_id']:22s} {r['noplaces_status']:11s}{r['noplaces_subjects']}"
                  f" -> {r['places_status']:11s}{r['places_subjects']}"
                  f" (receipts w/ places: {r['n_receipts_with_places']})")
    print("DONE")


if __name__ == "__main__":
    main()
