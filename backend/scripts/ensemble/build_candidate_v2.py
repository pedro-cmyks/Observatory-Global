"""Taxonomy revision — synthesize the ensemble proposals into candidate v2 (#204).

Merges the per-persona proposals (Phase B) into one candidate taxonomy:
 - category set = union by slug, tagged with which proposals included it (consensus
   signal: a slug both proposals keep is high-confidence; a slug only one keeps is
   contested → flagged for the gold phase).
 - includes/excludes = prefer the most specific text across proposals.
 - out_of_scope_policy = the orchestrator's merge (the core fix from Phase A).
Emits candidate-v2.json + a readable markdown table. Pure file synthesis, no LLM.
Run: python -m backend.scripts.ensemble.build_candidate_v2
"""
from __future__ import annotations

import glob
import json
import os

PROP_DIR = "docs/research/taxonomy-revision/proposals"
OUT_JSON = "docs/research/taxonomy-revision/candidate-v2.json"
OUT_MD = "docs/research/taxonomy-revision/candidate-v2.md"

# The synthesized OUT_OF_SCOPE policy — the structural fix Phase A proved is missing.
OUT_OF_SCOPE_POLICY = (
    "Atlas tracks SIGNIFICANT crisis/risk narratives only. Reject (OUT_OF_SCOPE) any "
    "signal that is not substantively about an acute or developing crisis/risk with "
    "potential for significant harm, disruption, or instability. Reject even when a "
    "crisis WORD appears if the signal is really about something else. Explicit "
    "rejects: routine business/markets, sport, culture/entertainment, book/film "
    "reviews, shopping/product/lifestyle, local human-interest or memorials, "
    "celebrity, ordinary weather forecasts, procedural/legal items that are not "
    "themselves a crisis, and satire. A category is assigned ONLY if the signal "
    "clears this bar AND matches that category's `includes` without hitting its "
    "`excludes`."
)

# Orchestrator (geopolitics-analyst lens) additions flagged for the gold phase —
# real gaps in the current crisis space, not yet ensemble-validated.
FLAGGED_ADDITIONS = [
    {"slug": "earthquake-volcano-disaster", "label": "Earthquake or volcanic disaster",
     "parent_domain": "climate-disaster",
     "definition": "Seismic or volcanic events causing casualties, damage, or evacuation.",
     "includes": "earthquakes, aftershocks, tsunamis, volcanic eruptions, ashfall evacuations",
     "excludes": "routine seismology research; disaster anniversaries; flood/landslide (own category)",
     "_status": "FLAGGED_ADD (orchestrator) — closes a natural-hazard gap; validate in gold"},
    {"slug": "wildfire-storm-disaster", "label": "Wildfire or severe-storm disaster",
     "parent_domain": "climate-disaster",
     "definition": "Wildfires, hurricanes/cyclones, tornadoes, or severe storms causing harm.",
     "includes": "wildfires, hurricanes, typhoons, cyclones, tornadoes, blizzards causing damage",
     "excludes": "ordinary weather forecasts; heat without fire/storm (heat-health category)",
     "_status": "FLAGGED_ADD (orchestrator) — closes a natural-hazard gap; validate in gold"},
]


def _len(s) -> int:
    return len(s) if isinstance(s, str) else 0


def main() -> int:
    proposals = []
    for path in sorted(glob.glob(f"{PROP_DIR}/*.json")):
        with open(path) as f:
            proposals.append(json.load(f))
    if not proposals:
        print(f"no proposals in {PROP_DIR}")
        return 1

    merged: dict[str, dict] = {}
    support: dict[str, list[str]] = {}
    for prop in proposals:
        persona = prop.get("_persona", prop.get("_provider", "?"))
        for c in prop.get("categories", []):
            slug = c.get("slug")
            if not slug:
                continue
            support.setdefault(slug, []).append(persona)
            cur = merged.get(slug, {})
            # keep the most specific text per field
            for field in ("label", "parent_domain", "definition", "includes", "excludes"):
                if _len(c.get(field)) > _len(cur.get(field)):
                    cur[field] = c.get(field)
            cur["slug"] = slug
            merged[slug] = cur

    n_props = len(proposals)
    categories = []
    for slug, c in sorted(merged.items(), key=lambda kv: kv[0]):
        c["_support"] = support[slug]
        c["_consensus"] = "all" if len(support[slug]) == n_props else "partial"
        categories.append(c)
    for add in FLAGGED_ADDITIONS:
        categories.append(add)

    candidate = {
        "version": "candidate-v2",
        "method": "multi-model/multi-persona ensemble synthesis (#204)",
        "personas": [p.get("_persona") for p in proposals],
        "out_of_scope_policy": OUT_OF_SCOPE_POLICY,
        "n_categories": len(categories),
        "categories": categories,
    }
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w") as f:
        json.dump(candidate, f, indent=2, ensure_ascii=False)

    lines = ["# Candidate taxonomy v2 (#204 ensemble synthesis)", "",
             f"Personas: {', '.join(candidate['personas'])} + orchestrator (geopolitics-analyst).",
             f"{len(categories)} categories. **The core change is the OUT_OF_SCOPE reject policy** "
             "(Phase A proved ~30–46% of gate-kept evidence is force-fit).", "",
             "## OUT_OF_SCOPE policy", "", OUT_OF_SCOPE_POLICY, "",
             "## Categories", "", "| consensus | slug | label | excludes (anti-force-fit) |",
             "|---|---|---|---|"]
    for c in categories:
        con = c.get("_consensus", c.get("_status", "?"))
        con = "ALL" if con == "all" else ("partial" if con == "partial" else "FLAGGED")
        lines.append(f"| {con} | `{c['slug']}` | {c.get('label','')} | "
                     f"{(c.get('excludes') or '')[:80]} |")
    with open(OUT_MD, "w") as f:
        f.write("\n".join(lines) + "\n")

    allc = sum(1 for c in categories if c.get("_consensus") == "all")
    part = sum(1 for c in categories if c.get("_consensus") == "partial")
    flag = sum(1 for c in categories if c.get("_status"))
    print(f"candidate v2: {len(categories)} categories "
          f"({allc} all-consensus, {part} partial, {flag} flagged-add)")
    print(f"  → {OUT_JSON}\n  → {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
