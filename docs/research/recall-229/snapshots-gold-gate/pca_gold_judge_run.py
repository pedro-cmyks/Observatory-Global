"""Gold-gate judge for the PCA-128 dry-run pair (#229) — cost-capped run.

Adapted from gold_judge_run.py (the whitening judge, 2026-07-18): 40 marginal
PCA-formed clusters + 40 matched control clusters. DeepSeek temp-0 judges all
80; GPT-4o judges a 20-cluster random subset as a vendor-agreement spot check
(100 calls total, inside the ~100 cost guard).

Differences vs the whitening run: both dry-runs were snapshotted off the SAME
as_of (2026-07-19T23:30:46Z, `same_as_of: true` in pca-harness-summary.json),
so there is NO 27h window confound and no shared-window filter is needed
(old_member_frac is 1.0 for every marginal; asserted below). Marginal = PCA
kept cluster with <50% member overlap vs every control kept cluster in the
same country. Non-Latin monoculture stratum (RU/UA/CN/IR/GR) oversampled to
50% of the marginal sample per the harness gold-gate spec.

Reads the dumps from the session scratchpad (pca-control.json / pca-128.json,
~7 MB each, not committed); writes pca-gold-judgments.json next to them and
mirrors it into this directory for versioning.
"""
from __future__ import annotations

import asyncio
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

import httpx

sys.path.insert(0, "/Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal")
from backend.scripts.ensemble.model_clients import call_llm  # noqa: E402

GG = Path(__file__).parent
SCRATCH = Path(
    "/private/tmp/claude-501/-Users-pedro-Desktop-PEDRO-Cursos-ObservatorioGlobal/"
    "f9144380-cf02-49ba-ad81-905d8b823b00/scratchpad"
)
NONLATIN = {"RU", "UA", "CN", "IR", "GR"}
SEED = 229
MAX_HEADLINES = 12
CONCURRENCY = 5
N_MARGINAL = 40
N_CONTROL = 40
N_OPENAI_SPOT = 20

SYSTEM = (
    "You judge whether a set of news headlines, clustered by an algorithm, all "
    "cover the SAME real-world story/event (allowing direct follow-ups and "
    "reactions to that one event). Headlines may be in any language. "
    "Answer strict JSON: {\"same_story\": true|false, \"reason\": \"<one line>\"}. "
    "same_story=true only if a clear majority (>=80%) of the headlines are about "
    "one specific story; a grab-bag of unrelated topics is false."
)


def by_country(d):
    return {c["country"]: c for c in d["countries"]}


def build_samples(control, treated):
    cby, tby = by_country(control), by_country(treated)
    marginals = []
    for cc, t in tby.items():
        c_sets = [set(m["signal_id"] for m in cl["members"])
                  for cl in cby.get(cc, {}).get("clusters", [])]
        for tcl in t.get("clusters", []):
            tset = set(m["signal_id"] for m in tcl["members"])
            best = max((len(tset & cs) / max(len(tset), 1) for cs in c_sets),
                       default=0.0)
            if best < 0.5:
                marginals.append({"country": cc, "cluster": tcl,
                                  "best_control_overlap": round(best, 3)})

    rng = random.Random(SEED)
    nl = [m for m in marginals if m["country"] in NONLATIN]
    other = [m for m in marginals if m["country"] not in NONLATIN]
    rng.shuffle(nl)
    rng.shuffle(other)
    n_nl = min(len(nl), N_MARGINAL // 2)
    sample = nl[:n_nl] + other[: N_MARGINAL - n_nl]
    for m in sample:
        m["arm"] = "marginal"
        m["stratum"] = "nonlatin" if m["country"] in NONLATIN else "other"

    mix = Counter(m["country"] for m in sample)
    total_m = sum(mix.values())
    pool = defaultdict(list)
    for cc, c in cby.items():
        for ccl in c.get("clusters", []):
            pool[cc].append(ccl)
    for cc in pool:
        rng.shuffle(pool[cc])
    control_sample = []
    want = {cc: max(1, round(N_CONTROL * n / total_m)) for cc, n in mix.items()}
    for cc, n in want.items():
        for ccl in pool.get(cc, [])[:n]:
            control_sample.append(
                {"country": cc, "cluster": ccl, "arm": "control",
                 "stratum": "nonlatin" if cc in NONLATIN else "other"})
    used = {id(x["cluster"]) for x in control_sample}
    for cc in mix:
        for ccl in pool.get(cc, []):
            if len(control_sample) >= N_CONTROL:
                break
            if id(ccl) not in used:
                used.add(id(ccl))
                control_sample.append(
                    {"country": cc, "cluster": ccl, "arm": "control",
                     "stratum": "nonlatin" if cc in NONLATIN else "other"})
    return marginals, sample, control_sample[:N_CONTROL]


async def judge_one(item, provider, client, sem):
    cl = item["cluster"]
    heads = [m["headline"] for m in cl["members"][:MAX_HEADLINES]]
    user = ("Country batch: " + item["country"] + "\nHeadlines:\n" +
            "\n".join(f"{i+1}. {h}" for i, h in enumerate(heads)) +
            "\n\nDo these cover the same story? JSON only.")
    async with sem:
        try:
            txt = await call_llm(provider, system=SYSTEM, user=user,
                                 client=client, max_tokens=200,
                                 temperature=0.0, json_mode=True)
            d = json.loads(txt)
            return {"same_story": bool(d.get("same_story")),
                    "reason": str(d.get("reason", ""))[:200]}
        except Exception as ex:  # noqa: BLE001
            return {"same_story": None, "reason": f"ERROR: {ex}"[:200]}


async def main():
    control = json.loads((SCRATCH / "pca-control.json").read_text())
    treated = json.loads((SCRATCH / "pca-128.json").read_text())
    assert control["meta"].get("as_of") == treated["meta"].get("as_of"), \
        "as_of mismatch — window confound; re-run the pair off one snapshot"
    marginals, sample, control_sample = build_samples(control, treated)
    items = sample + control_sample
    print(f"marginal universe={len(marginals)} sampled={len(sample)} "
          f"(nonlatin={sum(1 for m in sample if m['stratum'] == 'nonlatin')}) "
          f"control={len(control_sample)}", file=sys.stderr)

    rng = random.Random(SEED + 1)
    spot_idx = set(rng.sample(range(len(items)), min(N_OPENAI_SPOT, len(items))))

    sem = asyncio.Semaphore(CONCURRENCY)
    async with httpx.AsyncClient(timeout=60.0) as client:
        ds = await asyncio.gather(
            *[judge_one(it, "deepseek", client, sem) for it in items])
        oa_tasks = {i: judge_one(items[i], "openai", client, sem)
                    for i in spot_idx}
        oa_res = await asyncio.gather(*oa_tasks.values())
        oa = dict(zip(oa_tasks.keys(), oa_res))

    out = []
    for i, (it, d) in enumerate(zip(items, ds)):
        cl = it["cluster"]
        out.append({
            "arm": it["arm"], "stratum": it["stratum"],
            "country": it["country"], "cluster_id": cl.get("cluster_id"),
            "label": cl.get("label", "")[:120],
            "kept_size": cl.get("kept_size"), "cohesion": cl.get("cohesion"),
            "best_control_overlap": it.get("best_control_overlap"),
            "headlines": [m["headline"] for m in cl["members"][:MAX_HEADLINES]],
            "deepseek": d, "openai": oa.get(i),
        })

    def stats(rows):
        judged = [r for r in rows if r["deepseek"]["same_story"] is not None]
        yes = sum(1 for r in judged if r["deepseek"]["same_story"])
        return {"n": len(rows), "errors": len(rows) - len(judged),
                "same_story_yes": yes,
                "precision_pct": round(100 * yes / len(judged), 1) if judged else None}

    spot = [r for r in out if r["openai"] is not None
            and r["openai"]["same_story"] is not None
            and r["deepseek"]["same_story"] is not None]
    agree = sum(1 for r in spot
                if r["openai"]["same_story"] == r["deepseek"]["same_story"])
    summary = {
        "totals": {"marginal_universe": len(marginals),
                   "marginal_sampled": len(sample),
                   "control_sampled": len(control_sample)},
        "marginal": stats([r for r in out if r["arm"] == "marginal"]),
        "marginal_nonlatin": stats([r for r in out if r["arm"] == "marginal"
                                    and r["stratum"] == "nonlatin"]),
        "marginal_other": stats([r for r in out if r["arm"] == "marginal"
                                 and r["stratum"] == "other"]),
        "control": stats([r for r in out if r["arm"] == "control"]),
        "control_nonlatin": stats([r for r in out if r["arm"] == "control"
                                   and r["stratum"] == "nonlatin"]),
        "control_other": stats([r for r in out if r["arm"] == "control"
                                and r["stratum"] == "other"]),
        "vendor_spot_check": {"n": len(spot), "agree": agree,
                              "agree_pct": round(100 * agree / len(spot), 1)
                              if spot else None},
    }
    payload = json.dumps({"summary": summary, "clusters": out},
                         ensure_ascii=False, indent=1)
    (SCRATCH / "pca-gold-judgments.json").write_text(payload, encoding="utf-8")
    (GG / "pca-gold-judgments.json").write_text(payload, encoding="utf-8")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    asyncio.run(main())
