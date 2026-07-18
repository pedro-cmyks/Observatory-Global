"""Gold-gate judge for the whitening dry-run pair (#229) — cost-capped run.

Adapted from gold_judge.py (staged): 40 marginal whitened clusters + 40
matched control clusters. DeepSeek temp-0 judges all 80; GPT-4o judges a
20-cluster random subset as a vendor-agreement spot check (100 calls total,
inside the ~100 cost guard).

Marginal = whitened-kept cluster with <50% member overlap vs any control-kept
cluster in the same country, RESTRICTED to shared-window clusters (>=80% of
members existed at control snapshot time, by signal_id <= control max id) so
the 27h snapshot-time gap between the two dry-runs cannot masquerade as
whitening recall. Non-Latin monoculture stratum (RU/UA/CN/IR/GR) oversampled
to ~50% of the marginal sample per the harness gold-gate spec.
Writes gold-judgments.json.
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


def build_samples(control, whitened):
    cby, wby = by_country(control), by_country(whitened)
    c_max_id = max(m["signal_id"] for c in control["countries"]
                   for cl in c.get("clusters", []) for m in cl["members"])
    marginals = []
    for cc, w in wby.items():
        c_sets = [set(m["signal_id"] for m in cl["members"])
                  for cl in cby.get(cc, {}).get("clusters", [])]
        for wcl in w.get("clusters", []):
            wset = set(m["signal_id"] for m in wcl["members"])
            best = max((len(wset & cs) / max(len(wset), 1) for cs in c_sets),
                       default=0.0)
            old_frac = sum(1 for i in wset if i <= c_max_id) / len(wset)
            if best < 0.5 and old_frac >= 0.8:
                marginals.append({"country": cc, "cluster": wcl,
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
    control = json.loads((GG / "control.json").read_text())
    whitened = json.loads((GG / "whitened.json").read_text())
    marginals, sample, control_sample = build_samples(control, whitened)
    items = sample + control_sample
    print(f"shared-window marginal universe={len(marginals)} "
          f"sampled={len(sample)} "
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
        "totals": {"shared_window_marginal_universe": len(marginals),
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
    (GG / "gold-judgments.json").write_text(
        json.dumps({"summary": summary, "clusters": out},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    asyncio.run(main())
