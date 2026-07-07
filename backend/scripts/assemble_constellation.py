#!/usr/bin/env python
"""Constellation assembly — turn an umbrella's ~30 near-duplicate/facet fragments
into ONE canonical event with typed sub-facets (2026-07-06).

Spec: docs/specs/2026-07-06-connection-layer-constellation-assembly.md §A.
Builds ON the existing umbrella hierarchy (build_umbrella_topics.py /
robot_apply_outputs.py already parent same-EVENT children via parent_id). This
pass adds the THREE things those leave undone:

  1. ATTACH ORPHANS — a non-umbrella topic whose e5 centroid is >= --attach-threshold
     (default 0.90) to an umbrella's centroid but was left un-parented (missed the
     robot's groups.json snapshot). Semantic, geo-independent → facets attach to the
     right umbrella regardless of geo-tag noise (#238). Reversible.
  2. RELABEL a FACET-POLLUTED umbrella — robot_apply_outputs labels an umbrella with
     its biggest child's label, so "Venezuela Earthquake Death Toll" (a facet) became
     the event name. When the umbrella label itself types as a facet, relabel to the
     canonical event stem (top doc-frequency content tokens) → "Venezuela Earthquake".
  3. TYPE each child's FACET — the R3 category lens applied WITHIN the umbrella, at a
     finer event-internal vocabulary: death-toll / foreign-victims / rescues /
     international-aid / government-response / aftermath. Lexical (multilingual), the
     same deterministic idiom as the native geo/subject typers.

Reversible: UPDATE dynamic_topics SET facet=NULL; parent_id restore is the umbrella
build's concern. Dry-run by default; --apply writes.

Usage:
  python backend/scripts/assemble_constellation.py                    # dry-run all umbrellas
  python backend/scripts/assemble_constellation.py --umbrella 1837    # one umbrella
  python backend/scripts/assemble_constellation.py --apply
"""
from __future__ import annotations

import argparse
import asyncio
import os
import re
import sys
from collections import Counter

import numpy as np

# ── Facet lexicon (priority order; first match wins) ─────────────────────────
# Generic event tokens (earthquake/quake/terremoto/sismo/venezuela/magnitude) are
# DELIBERATELY excluded — they are in every child and would collapse all facets
# into one. A facet keys on the NARRATIVE ANGLE word, not the event word.
_FACET_LEXICON: list[tuple[str, str]] = [
    # nationality-scoped victims FIRST — "Spanish Deaths" is foreign-victims, not death-toll
    ("foreign-victims",
     r"\b(italian|spanish|portuguese|french|german|foreign|extranjer\w*|"
     r"italiano?s?|espa[ñn]ol\w*|portugues\w*|franc[eé]s\w*|nationals?|"
     r"repatriat\w*|repatriac\w*)\b"),
    ("rescues",
     r"\b(rescue\w*|rescat\w*|search[- ]and[- ]rescue|survivor\w*|"
     r"sobrevivient\w*|trapped|atrapad\w*|dig\w* out)\b"),
    ("international-aid",
     r"\b(aid|ayuda|relief|humanitarian|humanitari\w*|donation\w*|donac\w*|"
     r"\bun\b|\bonu\b|afectad\w*|affected|assistance|assist\w*|solidarid\w*|"
     r"aporte\w*|pledge\w*)\b"),
    ("government-response",
     r"\b(government|gobierno|inspection\w*|inspec\w*|risk|riesgo\w*|response|"
     r"respuesta|interim|delcy|epidemi\w*|prevent\w*|decree\w*|decret\w*|"
     r"emergency|emergenc\w*|state of|evacuat\w*|evacuac\w*)\b"),
    ("aftermath",
     r"\b(aftermath|reconstruct\w*|reconstrucc\w*|recovery|recuper\w*|"
     r"rebuild\w*|secuel\w*|damage assess\w*)\b"),
    # core impact — NO generic event word, so a pure "Venezuela Earthquake" stays 'core'
    ("death-toll",
     r"\b(death toll|deaths?|casualt\w*|kill\w*|muert\w*|v[ií]ctimas?|"
     r"fallecid\w*|tragedy|traged\w*|disaster|desastr\w*|collapse|colaps\w*|"
     r"toll|dead)\b"),
]

# generic hazard/event nouns — present in MANY unrelated events, so useless as the
# discriminating anchor for orphan attachment (a Lakonia quake shares "earthquake"
# with a Venezuela quake but is a different event). The SUBJECT token (country/proper
# noun) is what binds an orphan to the right umbrella.
_GENERIC_EVENT = {
    "earthquake", "quake", "terremoto", "sismo", "seisme", "seismo", "temblor",
    "tsunami", "flood", "flooding", "wildfire", "bushfire", "fire", "hurricane",
    "typhoon", "cyclone", "tornado", "storm", "war", "conflict", "attack",
    "shooting", "explosion", "crisis", "heatwave", "match", "cup", "tournament",
    "protest", "strike", "election", "vote", "summit", "talks", "deal", "cross",
    "border", "alert", "report", "emerging", "news", "double", "google",
}

# tokens stripped when deriving the canonical event stem (facet/measure words + numbers)
_STEM_STOP = {
    "the", "and", "of", "in", "for", "on", "to", "de", "la", "el", "los", "las",
    "updates", "update", "news", "coverage", "crisis", "2026", "vs",
    "death", "toll", "deaths", "dead", "kill", "kills", "casualties", "casualty",
    "tragedy", "disaster", "collapse", "aftermath", "rescue", "rescues", "aid",
    "victims", "victim", "estimates", "affected", "afectados", "muertos",
}


def facet_of(label: str) -> str:
    """Type a child label to its event-internal facet (lexical, multilingual)."""
    s = (label or "").lower()
    for facet, pat in _FACET_LEXICON:
        if re.search(pat, s, re.I):
            return facet
    return "core"


def canonical_stem(labels: list[str], biggest_label: str) -> str:
    """Derive the event name from the children: the highest-doc-frequency content
    tokens (>=40% of children), ordered by first appearance in the biggest child's
    label. Plurals normalized for counting (earthquakes==earthquake)."""
    def toks(s: str) -> list[str]:
        return [t for t in re.findall(r"[a-zà-ÿ]{3,}", s.lower()) if t not in _STEM_STOP]

    def norm(t: str) -> str:
        return t[:-1] if t.endswith("s") and len(t) > 4 else t

    df: Counter[str] = Counter()
    for l in labels:
        df.update({norm(t) for t in toks(l)})
    n = max(1, len(labels))
    core = {t for t, c in df.items() if c >= 0.4 * n}
    if not core:
        return biggest_label
    # order + surface form from the biggest child's label
    ordered: list[str] = []
    seen: set[str] = set()
    for raw in re.findall(r"[A-Za-zà-ÿ]{3,}", biggest_label):
        nt = norm(raw.lower())
        if nt in core and nt not in seen:
            ordered.append(raw[:1].upper() + raw[1:].lower())
            seen.add(nt)
    for t in sorted(core - seen, key=lambda t: -df[t]):
        ordered.append(t.capitalize())
    return " ".join(ordered) if ordered else biggest_label


def _cos_to(cen: np.ndarray, M: np.ndarray) -> np.ndarray:
    M = M / (np.linalg.norm(M, axis=1, keepdims=True) + 1e-9)
    return M @ (cen / (np.linalg.norm(cen) + 1e-9))


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--umbrella", type=int, default=None, help="one umbrella id (default: all)")
    ap.add_argument("--attach-threshold", type=float, default=0.93,
                    help="min centroid cosine to attach an orphan (needs signature-token overlap too)")
    ap.add_argument("--all", action="store_true",
                    help="required to --apply across ALL umbrellas (broad relabel/attach "
                         "is risky in e5's compressed space — see 2026-07-06 dry-run: "
                         "sports/crime over-attach + label breakage; prefer per-umbrella)")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    if args.apply and not args.umbrella and not args.all:
        print("refusing broad --apply without --all (per-umbrella review recommended); "
              "use --umbrella <id> --apply, or --all --apply if you have reviewed the dry-run",
              file=sys.stderr)
        return 2

    import asyncpg
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL not set", file=sys.stderr)
        return 2
    conn = await asyncpg.connect(dsn, statement_cache_size=0)
    try:
        where = "AND id = $1" if args.umbrella else ""
        umbrellas = await conn.fetch(
            f"""SELECT id, label, centroid_vec FROM dynamic_topics
                WHERE is_umbrella = true AND centroid_vec IS NOT NULL {where}
                ORDER BY agg_n_signals DESC""",
            *([args.umbrella] if args.umbrella else []))
        if not umbrellas:
            print("no umbrellas match", file=sys.stderr)
            return 1

        # global token document-frequency across ALL topic labels — lets us tell
        # a DISCRIMINATING signature token ("venezuela", rare) from a generic event
        # word ("earthquake", in many unrelated quakes). Orphan attachment anchors
        # on the rare token so Lakonia/Philippines/Mexico quakes never merge in.
        gdf: Counter[str] = Counter()
        for r in await conn.fetch(
                "SELECT label FROM dynamic_topics WHERE label IS NOT NULL"):
            gdf.update({t[:-1] if t.endswith("s") and len(t) > 4 else t
                        for t in re.findall(r"[a-zà-ÿ]{4,}", r["label"].lower())
                        if t not in _STEM_STOP})

        # orphan pool: non-umbrella, un-parented, active-ish, with a centroid
        orphans = await conn.fetch(
            """SELECT id, label, centroid_vec FROM dynamic_topics
               WHERE is_umbrella = false AND parent_id IS NULL
                 AND centroid_vec IS NOT NULL AND state <> 'deprecated'""")
        O_ids = [int(r["id"]) for r in orphans]
        O = (np.asarray([list(r["centroid_vec"]) for r in orphans], dtype=np.float32)
             if orphans else np.zeros((0, 1), dtype=np.float32))

        def _sig_tokens(labels: list[str]) -> set[str]:
            """Distinctive content tokens shared by >=40% of an umbrella's trusted
            children — the event signature that gates orphan attachment. e5 centroid
            space is compressed (p50 0.94), so cosine alone floods; the lexical
            signature is the guard (same idiom as robot's dominant-token)."""
            df: Counter[str] = Counter()
            for l in labels:
                df.update({t[:-1] if t.endswith("s") and len(t) > 4 else t
                           for t in re.findall(r"[a-zà-ÿ]{4,}", (l or "").lower())
                           if t not in _STEM_STOP})
            n = max(1, len(labels))
            return {t for t, c in df.items() if c >= 0.4 * n}

        def _label_tokens(label: str) -> set[str]:
            return {t[:-1] if t.endswith("s") and len(t) > 4 else t
                    for t in re.findall(r"[a-zà-ÿ]{4,}", (label or "").lower())}

        taken: set[int] = set()  # orphans claimed by an earlier umbrella this run
        total_attached = total_relabeled = total_typed = 0
        for u in umbrellas:
            uid = int(u["id"])
            ucen = np.asarray(list(u["centroid_vec"]), dtype=np.float32)

            existing = await conn.fetch(
                "SELECT id, label FROM dynamic_topics WHERE parent_id = $1", uid)
            if len(existing) < 2:
                continue  # trust the umbrella build; assemble only real umbrellas
            trusted_labels = [r["label"] for r in existing]
            signature = _sig_tokens(trusted_labels)
            # anchor = signature MINUS generic hazard/event words → the discriminating
            # subject tokens ("venezuela"). Fallback to the globally-rarest signature
            # token if an umbrella's signature is all-generic (rare).
            anchor = signature - _GENERIC_EVENT
            if not anchor and signature:
                min_gdf = min(gdf.get(t, 1) for t in signature)
                anchor = {t for t in signature if gdf.get(t, 1) == min_gdf}

            # 1. attach orphans: high cosine AND shares a discriminating anchor token
            #    (lexical guard kills the compressed-space flood; reversible)
            attached: list[tuple[int, str, float]] = []
            if len(O_ids) and anchor:
                sims = _cos_to(ucen, O)
                for k, s in enumerate(sims):
                    oid = O_ids[k]
                    if (s >= args.attach_threshold and oid not in taken
                            and (_label_tokens(orphans[k]["label"]) & anchor)):
                        attached.append((oid, orphans[k]["label"], float(s)))
                        taken.add(oid)

            child_ids = [cid for cid, _, _ in attached]  # pending-attach
            all_children = [(int(r["id"]), r["label"]) for r in existing] + \
                           [(cid, lbl) for cid, lbl, _ in attached]
            labels = [lbl for _, lbl in all_children]
            # canonical stem derived from TRUSTED children only (orphans can't skew it)
            biggest_label = max(trusted_labels, key=lambda l: len(l or ""))

            # 2. relabel if the umbrella label itself types as a facet (pollution)
            new_label = u["label"]
            if facet_of(u["label"]) != "core":
                cand = canonical_stem(trusted_labels, biggest_label)
                if cand and cand.lower() != (u["label"] or "").lower():
                    new_label = cand

            # 3. type every child's facet
            facets = {cid: facet_of(lbl) for cid, lbl in all_children}
            dist = Counter(facets.values())

            print(f"\n■ umbrella {uid}  \"{u['label']}\"" +
                  (f"  → RELABEL → \"{new_label}\"" if new_label != u["label"] else ""))
            if attached:
                print(f"  attach {len(attached)} orphan(s): " +
                      ", ".join(f"{cid}({s:.2f})" for cid, _, s in attached))
            print(f"  facets: {dict(dist)}")
            for cid, lbl in sorted(all_children, key=lambda x: facets[x[0]]):
                print(f"    [{facets[cid]:>18}] {cid:>5}  {str(lbl)[:52]}")

            if args.apply:
                if child_ids:
                    await conn.execute(
                        "UPDATE dynamic_topics SET parent_id=$1, updated_at=now() "
                        "WHERE id = ANY($2::bigint[])", uid, child_ids)
                    total_attached += len(child_ids)
                if new_label != u["label"]:
                    await conn.execute(
                        "UPDATE dynamic_topics SET label=$1, updated_at=now() WHERE id=$2",
                        new_label, uid)
                    total_relabeled += 1
                for cid, f in facets.items():
                    await conn.execute(
                        "UPDATE dynamic_topics SET facet=$1, updated_at=now() WHERE id=$2",
                        f, cid)
                total_typed += len(facets)

        verb = "APPLIED" if args.apply else "DRY-RUN"
        print(f"\n{verb}: attached={total_attached} relabeled={total_relabeled} "
              f"children_typed={total_typed}")
    finally:
        await conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
