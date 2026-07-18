"""Pair sanity + marginal computation for the gold-gate dry-run pair.

Reads control.json + whitened.json (per-country cluster payloads from
run_scoped_snapshot --dump-json), writes pair-summary.json:
  per-country: control_kept, whitened_kept, marginal_count
  marginal = whitened kept cluster whose best member-overlap with ANY control
  cluster in the same country is < 50% (overlap = |W∩C| / |W|).
"""
import json
import sys
from pathlib import Path

GG = Path(__file__).parent
control = json.loads((GG / "control.json").read_text())
whitened = json.loads((GG / "whitened.json").read_text())


def by_country(d):
    return {c["country"]: c for c in d["countries"]}


cby, wby = by_country(control), by_country(whitened)
c_ccs, w_ccs = set(cby), set(wby)

per_country = {}
tot_c = tot_w = tot_m = 0
marginal_examples = []
for cc in sorted(c_ccs | w_ccs):
    c_clusters = cby.get(cc, {}).get("clusters", [])
    w_clusters = wby.get(cc, {}).get("clusters", [])
    c_sets = [set(m["signal_id"] for m in cl["members"]) for cl in c_clusters]
    marginal = 0
    for wcl in w_clusters:
        wset = set(m["signal_id"] for m in wcl["members"])
        best = max((len(wset & cs) / max(len(wset), 1) for cs in c_sets), default=0.0)
        if best < 0.5:
            marginal += 1
            if len(marginal_examples) < 25:
                marginal_examples.append({
                    "country": cc,
                    "kept_size": wcl["kept_size"],
                    "cohesion": round(wcl["cohesion"], 4),
                    "best_control_overlap": round(best, 3),
                    "sample_headlines": [m["headline"][:110] for m in wcl["members"][:3]],
                })
    per_country[cc] = {
        "control_kept": len(c_clusters),
        "whitened_kept": len(w_clusters),
        "marginal_count": marginal,
    }
    tot_c += len(c_clusters)
    tot_w += len(w_clusters)
    tot_m += marginal

summary = {
    "meta": {
        "control": control["meta"],
        "whitened": whitened["meta"],
        "countries_match": c_ccs == w_ccs,
        "control_only_countries": sorted(c_ccs - w_ccs),
        "whitened_only_countries": sorted(w_ccs - c_ccs),
    },
    "totals": {
        "control_kept_clusters": tot_c,
        "whitened_kept_clusters": tot_w,
        "marginal_whitened_not_in_control": tot_m,
    },
    "per_country": per_country,
    "marginal_examples": marginal_examples,
}
out = GG / "pair-summary.json"
out.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps({"totals": summary["totals"],
                  "countries_match": summary["meta"]["countries_match"],
                  "control_only": summary["meta"]["control_only_countries"],
                  "whitened_only": summary["meta"]["whitened_only_countries"]},
                 indent=1))
print("written:", out, file=sys.stderr)
