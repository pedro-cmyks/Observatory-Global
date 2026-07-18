"""Structural stats for the whitening gold-gate pair (#229).

Beyond pair_summary.py: ge12 promotable counts, cohesion distributions,
max-cluster (blob) check, and a window-shift de-confound — the two dry-runs
were snapshotted 27h apart (control 07-16T20:10, whitened 07-17T23:00, both
168h windows), so ~27h of signals differ at each end. A whitened cluster made
of window-new signals is NOT whitening's marginal recall. We tag each marginal
cluster by the fraction of its members whose signal_id <= the max signal_id
seen anywhere in the control dump (id monotonicity ~ ingest time):
  shared-window marginal = >=80% members existed at control snapshot time.
Writes structural-stats.json.
"""
import json
from pathlib import Path
from statistics import mean, median

GG = Path(__file__).parent
control = json.loads((GG / "control.json").read_text())
whitened = json.loads((GG / "whitened.json").read_text())


def by_country(d):
    return {c["country"]: c for c in d["countries"]}


def all_clusters(d):
    out = []
    for c in d["countries"]:
        for cl in c.get("clusters", []):
            out.append((c["country"], cl))
    return out


cby, wby = by_country(control), by_country(whitened)
c_all, w_all = all_clusters(control), all_clusters(whitened)

c_max_id = max(m["signal_id"] for _, cl in c_all for m in cl["members"])
w_min_id = min(m["signal_id"] for _, cl in w_all for m in cl["members"])


def arm_stats(clusters):
    kept = [cl["kept_size"] for _, cl in clusters]
    coh = [cl["cohesion"] for _, cl in clusters]
    ge12 = [k for k in kept if k >= 12]
    biggest = max(clusters, key=lambda t: t[1]["kept_size"])
    return {
        "kept_clusters": len(kept),
        "ge12_promotable": len(ge12),
        "kept_signal_mass": sum(kept),
        "kept_p50": median(kept),
        "kept_max": max(kept),
        "kept_max_country": biggest[0],
        "kept_max_label": biggest[1].get("label", "")[:80],
        "mean_cohesion": round(mean(coh), 4),
        "p10_cohesion": round(sorted(coh)[int(0.1 * len(coh))], 4),
    }


# marginals (same rule as pair_summary: best member-overlap < 0.5 vs any
# control cluster in the same country, overlap = |W∩C|/|W|)
marginals = []
for cc, w in wby.items():
    c_sets = [set(m["signal_id"] for m in cl["members"])
              for cl in cby.get(cc, {}).get("clusters", [])]
    for wcl in w.get("clusters", []):
        wset = set(m["signal_id"] for m in wcl["members"])
        best = max((len(wset & cs) / max(len(wset), 1) for cs in c_sets),
                   default=0.0)
        if best < 0.5:
            old_frac = sum(1 for i in wset if i <= c_max_id) / len(wset)
            marginals.append({"country": cc, "cluster": wcl,
                              "best_control_overlap": round(best, 3),
                              "old_member_frac": round(old_frac, 3)})

shared = [m for m in marginals if m["old_member_frac"] >= 0.8]
windownew = [m for m in marginals if m["old_member_frac"] < 0.8]

# reverse marginals: control clusters lost in whitened (same rule mirrored)
lost = 0
for cc, c in cby.items():
    w_sets = [set(m["signal_id"] for m in cl["members"])
              for cl in wby.get(cc, {}).get("clusters", [])]
    for ccl in c.get("clusters", []):
        cset = set(m["signal_id"] for m in ccl["members"])
        best = max((len(cset & ws) / max(len(cset), 1) for ws in w_sets),
                   default=0.0)
        if best < 0.5:
            lost += 1

out = {
    "meta": {"control": control["meta"], "whitened": whitened["meta"],
             "control_max_signal_id": c_max_id,
             "whitened_min_signal_id": w_min_id},
    "control": arm_stats(c_all),
    "whitened": arm_stats(w_all),
    "marginal": {
        "total": len(marginals),
        "shared_window_ge80pct_old": len(shared),
        "window_new_lt80pct_old": len(windownew),
        "shared_ge12": sum(1 for m in shared if m["cluster"]["kept_size"] >= 12),
        "total_ge12": sum(1 for m in marginals if m["cluster"]["kept_size"] >= 12),
        "shared_mean_cohesion": round(mean(m["cluster"]["cohesion"] for m in shared), 4) if shared else None,
        "control_clusters_lost_in_whitened": lost,
    },
}
(GG / "structural-stats.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
