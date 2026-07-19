"""#229 PCA-128 clustering-input harness — compare step (control vs PCA dumps).

The "make Atlas lighter" lever, measured not guessed. Forensics 2026-07-19:
HDBSCAN's brute O(n²·d) MST is ~85% of the nightly snapshot cost at d=768;
per-country PCA to 128 dims should be ~6× cheaper (archive-engine precedent:
archive_cluster_offline.cluster_scope PCA-128, mig 074b) — IF the clusters it
forms are the same substrate. This script judges a `run_scoped_snapshot
--dump-json` dry-run PAIR over the SAME frozen window (--as-of):

  control:  --pca-dim 0            (raw 768-d e5, current production)
  pca:      ATLAS_CLUSTER_PCA_DIM=128 (reduced HDBSCAN input; centroids/gate/
                                      persisted space stay raw e5)

and emits cluster counts, ≥12 promotable (volume_min proxy), cohesion deltas,
max-cluster size (blob check), per-country wall-time, and a verdict against
PRE-REGISTERED bars — the whitening gold gate's bars (2026-07-18-whitening-
gold-gate.md) plus the speed bar this lever exists for:

  1. YIELD    kept clusters (write floor ≥8) drop ≤ 10% vs control
  2. YIELD    ≥12 promotable (volume_min proxy) drop ≤ 10% vs control
  3. MARGINAL mean raw-space cohesion of PCA-marginal clusters within 10pp
              (0.10) of the control-arm mean — a STRUCTURAL proxy for the
              whitening gate's judged same-story bar; if the marginal fraction
              exceeds 15% of PCA clusters, structure is insufficient and the
              verdict is capped at JUDGE_REQUIRED (run the gold-judge
              machinery: docs/research/recall-229/snapshots-gold-gate/
              gold_judge_run.py on the marginals this script lists)
  4. BLOB     max kept cluster ≤ 1.5× control's max (no mega-blob)
  5. SPEED    Σ control cluster_seconds / Σ pca cluster_seconds ≥ 4× over
              countries timed in BOTH arms (the claim that justifies wiring)

Window de-confound (structural_stats.py rule): even with --as-of frozen, the
embed cron can add vectors for old signals between the two runs — marginals
are split by old_member_frac (≥80% of members ≤ the control dump's max
signal_id = genuinely re-partitioned, not corpus drift).

Read-only over the two JSON dumps; writes a summary JSON + prints the verdict.

Usage (M1 mlvenv or any python3 with stdlib):
  python -m backend.scripts.pca_recall_harness \
      --control /path/pca-control.json --pca /path/pca-128.json \
      --out /path/pca-harness-summary.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from statistics import mean, median

# ---------------------------------------------------------- pre-registered bars
YIELD_DROP_MAX = 0.10        # bars 1+2: ≤10% drop in kept / ge12 counts
MARGINAL_COHESION_PP = 0.10  # bar 3: marginal mean cohesion within 10pp of control mean
MARGINAL_JUDGE_FRAC = 0.15   # bar 3 cap: >15% marginal clusters ⇒ JUDGE_REQUIRED
BLOB_FACTOR = 1.5            # bar 4: pca max kept ≤ 1.5× control max kept
SPEED_BAR = 4.0              # bar 5: measured clustering speedup ≥ 4×
MARGINAL_OVERLAP = 0.5       # marginal = best member-overlap < 0.5 (gold-gate rule)
OLD_FRAC_SHARED = 0.8        # shared-window marginal = ≥80% members pre-existed


def _all_clusters(dump: dict) -> list[tuple[str, dict]]:
    out = []
    for c in dump.get("countries", []):
        for cl in c.get("clusters", []):
            out.append((c["country"], cl))
    return out


def _by_country(dump: dict) -> dict[str, dict]:
    return {c["country"]: c for c in dump.get("countries", [])}


def arm_stats(clusters: list[tuple[str, dict]]) -> dict:
    """Structural stats for one arm (same shape as structural_stats.py)."""
    if not clusters:
        return {"kept_clusters": 0, "ge12_promotable": 0, "kept_signal_mass": 0,
                "kept_p50": None, "kept_max": 0, "kept_max_country": None,
                "kept_max_label": None, "mean_cohesion": None, "p10_cohesion": None}
    kept = [cl["kept_size"] for _, cl in clusters]
    coh = [cl["cohesion"] for _, cl in clusters if cl.get("cohesion") is not None]
    biggest = max(clusters, key=lambda t: t[1]["kept_size"])
    return {
        "kept_clusters": len(kept),
        "ge12_promotable": sum(1 for k in kept if k >= 12),
        "kept_signal_mass": sum(kept),
        "kept_p50": median(kept),
        "kept_max": max(kept),
        "kept_max_country": biggest[0],
        "kept_max_label": (biggest[1].get("label") or "")[:80],
        "mean_cohesion": round(mean(coh), 4) if coh else None,
        "p10_cohesion": round(sorted(coh)[int(0.1 * len(coh))], 4) if coh else None,
    }


def find_marginals(control: dict, treated: dict) -> list[dict]:
    """Treated clusters with best same-country member-overlap < 0.5 vs control,
    tagged with the shared-window de-confound fraction (structural_stats rule)."""
    cby = _by_country(control)
    c_all = _all_clusters(control)
    c_max_id = max((m["signal_id"] for _, cl in c_all for m in cl["members"]),
                   default=0)
    out = []
    for cc, tc in _by_country(treated).items():
        c_sets = [set(m["signal_id"] for m in cl["members"])
                  for cl in cby.get(cc, {}).get("clusters", [])]
        for tcl in tc.get("clusters", []):
            tset = set(m["signal_id"] for m in tcl["members"])
            if not tset:
                continue
            best = max((len(tset & cs) / len(tset) for cs in c_sets), default=0.0)
            if best < MARGINAL_OVERLAP:
                old_frac = sum(1 for i in tset if i <= c_max_id) / len(tset)
                out.append({"country": cc,
                            "label": (tcl.get("label") or "")[:80],
                            "kept_size": tcl["kept_size"],
                            "cohesion": tcl.get("cohesion"),
                            "best_control_overlap": round(best, 3),
                            "old_member_frac": round(old_frac, 3)})
    return out


def count_lost(control: dict, treated: dict) -> int:
    """Control clusters with no ≥0.5 member-overlap match in the treated arm."""
    tby = _by_country(treated)
    lost = 0
    for cc, c in _by_country(control).items():
        t_sets = [set(m["signal_id"] for m in cl["members"])
                  for cl in tby.get(cc, {}).get("clusters", [])]
        for ccl in c.get("clusters", []):
            cset = set(m["signal_id"] for m in ccl["members"])
            if not cset:
                continue
            best = max((len(cset & ts) / len(cset) for ts in t_sets), default=0.0)
            if best < MARGINAL_OVERLAP:
                lost += 1
    return lost


def timing_stats(control: dict, treated: dict) -> dict:
    """Per-country clustering wall-time over countries timed in BOTH arms."""
    ct = {c["country"]: c.get("cluster_seconds")
          for c in control.get("countries", [])}
    tt = {c["country"]: c.get("cluster_seconds")
          for c in treated.get("countries", [])}
    matched = sorted(cc for cc in ct
                     if ct.get(cc) is not None and tt.get(cc) is not None)
    rows = [{"country": cc, "control_s": ct[cc], "pca_s": tt[cc],
             "speedup": round(ct[cc] / tt[cc], 2) if tt[cc] else None}
            for cc in matched]
    c_sum = sum(ct[cc] for cc in matched)
    t_sum = sum(tt[cc] for cc in matched)
    speedups = [r["speedup"] for r in rows if r["speedup"] is not None]
    return {
        "countries_timed_both": len(matched),
        "control_cluster_s_sum": round(c_sum, 1),
        "pca_cluster_s_sum": round(t_sum, 1),
        "overall_speedup": round(c_sum / t_sum, 2) if t_sum > 0 else None,
        "median_country_speedup": round(median(speedups), 2) if speedups else None,
        "slowest_control_top10": sorted(rows, key=lambda r: -(r["control_s"] or 0))[:10],
    }


def evaluate_bars(c_stats: dict, p_stats: dict, marginals: list[dict],
                  timing: dict) -> dict:
    """Apply the pre-registered PASS bars. Pure — unit-tested."""
    bars: dict[str, dict] = {}

    ck, pk = c_stats["kept_clusters"], p_stats["kept_clusters"]
    bars["yield_kept_ge8"] = {
        "pass": bool(ck == 0 or pk >= ck * (1 - YIELD_DROP_MAX)),
        "control": ck, "pca": pk,
        "bar": f"drop <= {YIELD_DROP_MAX:.0%} vs control",
    }
    cg, pg = c_stats["ge12_promotable"], p_stats["ge12_promotable"]
    bars["yield_ge12_promotable"] = {
        "pass": bool(cg == 0 or pg >= cg * (1 - YIELD_DROP_MAX)),
        "control": cg, "pca": pg,
        "bar": f"drop <= {YIELD_DROP_MAX:.0%} vs control",
    }

    m_coh = [m["cohesion"] for m in marginals if m.get("cohesion") is not None]
    m_mean = round(mean(m_coh), 4) if m_coh else None
    c_mean = c_stats["mean_cohesion"]
    marg_frac = (len(marginals) / pk) if pk else 0.0
    coh_ok = (m_mean is None or c_mean is None
              or m_mean >= c_mean - MARGINAL_COHESION_PP)
    bars["marginal_quality"] = {
        "pass": bool(coh_ok),
        "judge_required": bool(marg_frac > MARGINAL_JUDGE_FRAC),
        "marginal_count": len(marginals),
        "marginal_fraction_of_pca": round(marg_frac, 3),
        "marginal_mean_cohesion": m_mean,
        "control_mean_cohesion": c_mean,
        "bar": (f"marginal mean cohesion within {MARGINAL_COHESION_PP} of control "
                f"mean (structural proxy); fraction > {MARGINAL_JUDGE_FRAC:.0%} "
                f"⇒ JUDGE_REQUIRED"),
    }

    cm, pm = c_stats["kept_max"], p_stats["kept_max"]
    bars["no_mega_blob"] = {
        "pass": bool(cm == 0 or pm <= cm * BLOB_FACTOR),
        "control_max": cm, "pca_max": pm,
        "bar": f"pca max kept <= {BLOB_FACTOR}x control max",
    }

    sp = timing.get("overall_speedup")
    bars["speed"] = {
        "pass": bool(sp is not None and sp >= SPEED_BAR),
        "measured_speedup": sp,
        "bar": (f">= {SPEED_BAR}x measured clustering speedup"
                + ("" if sp is not None else
                   " — UNMEASURED: dumps lack cluster_seconds (re-run with the "
                   "updated run_scoped_snapshot)")),
    }

    all_pass = all(b["pass"] for b in bars.values())
    if not all_pass:
        verdict = "FAIL"
    elif bars["marginal_quality"]["judge_required"]:
        verdict = "JUDGE_REQUIRED"
    else:
        verdict = "PASS"
    return {"verdict": verdict, "bars": bars}


def main() -> None:
    ap = argparse.ArgumentParser(description="#229 PCA harness compare step.")
    ap.add_argument("--control", required=True, help="control dump (--pca-dim 0)")
    ap.add_argument("--pca", required=True, help="treated dump (ATLAS_CLUSTER_PCA_DIM=128)")
    ap.add_argument("--out", default="", help="summary JSON path (default: "
                    "pca-harness-summary.json next to the pca dump)")
    args = ap.parse_args()

    control = json.loads(Path(args.control).read_text())
    treated = json.loads(Path(args.pca).read_text())

    c_all, p_all = _all_clusters(control), _all_clusters(treated)
    c_stats, p_stats = arm_stats(c_all), arm_stats(p_all)
    marginals = find_marginals(control, treated)
    shared = [m for m in marginals if m["old_member_frac"] >= OLD_FRAC_SHARED]
    timing = timing_stats(control, treated)
    result = evaluate_bars(c_stats, p_stats, marginals, timing)

    summary = {
        "meta": {
            "control": control.get("meta", {}),
            "pca": treated.get("meta", {}),
            "same_as_of": (control.get("meta", {}).get("as_of") is not None
                           and control.get("meta", {}).get("as_of")
                           == treated.get("meta", {}).get("as_of")),
        },
        "control": c_stats,
        "pca": p_stats,
        "marginal": {
            "total": len(marginals),
            "shared_window_ge80pct_old": len(shared),
            "window_new_lt80pct_old": len(marginals) - len(shared),
            "ge12": sum(1 for m in marginals if m["kept_size"] >= 12),
            "control_clusters_lost_in_pca": count_lost(control, treated),
            "clusters": marginals,
        },
        "timing": timing,
        **result,
    }

    out = Path(args.out) if args.out else Path(args.pca).parent / "pca-harness-summary.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=1),
                   encoding="utf-8")

    b = result["bars"]
    print(f"#229 PCA harness — control vs pca_dim="
          f"{treated.get('meta', {}).get('pca_dim')}")
    if not summary["meta"]["same_as_of"]:
        print("  WARN: dumps do not share a frozen --as-of window — "
              "structural deltas carry window drift")
    print(f"  kept >=8:   control {c_stats['kept_clusters']} → pca "
          f"{p_stats['kept_clusters']}   "
          f"[{'PASS' if b['yield_kept_ge8']['pass'] else 'FAIL'}]")
    print(f"  ge12 promo: control {c_stats['ge12_promotable']} → pca "
          f"{p_stats['ge12_promotable']}   "
          f"[{'PASS' if b['yield_ge12_promotable']['pass'] else 'FAIL'}]")
    print(f"  cohesion:   control {c_stats['mean_cohesion']} → pca "
          f"{p_stats['mean_cohesion']} · marginals {len(marginals)} "
          f"({b['marginal_quality']['marginal_fraction_of_pca']:.1%}, "
          f"mean coh {b['marginal_quality']['marginal_mean_cohesion']})   "
          f"[{'PASS' if b['marginal_quality']['pass'] else 'FAIL'}"
          f"{' +JUDGE' if b['marginal_quality']['judge_required'] else ''}]")
    print(f"  blob:       control max {c_stats['kept_max']} → pca max "
          f"{p_stats['kept_max']}   "
          f"[{'PASS' if b['no_mega_blob']['pass'] else 'FAIL'}]")
    print(f"  speed:      {timing['control_cluster_s_sum']}s → "
          f"{timing['pca_cluster_s_sum']}s over "
          f"{timing['countries_timed_both']} countries = "
          f"{timing['overall_speedup']}x (median/country "
          f"{timing['median_country_speedup']}x)   "
          f"[{'PASS' if b['speed']['pass'] else 'FAIL'}]")
    print(f"  VERDICT: {result['verdict']}")
    print(f"  summary written: {out}")
    if result["verdict"] != "PASS":
        sys.exit(1)


if __name__ == "__main__":
    main()
