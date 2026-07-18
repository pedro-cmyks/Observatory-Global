"""Label-fold pre-pass for the umbrella build (Lane B, 2026-07-18).

The Venezuela-earthquake incident exposed 15+ ACTIVE fragments where NINE carry
the literal identical label "Venezuela Earthquake Death Toll" — a LABEL-string
cluster before it is a centroid cluster. The LLM same-event judge (all ~800
active labels in one prompt, 4k-token response cap) under-emits or truncates at
that scale, so this cheap deterministic fold runs FIRST:

  normalize labels (strip digits/dates, drop stopwords + the "Emerging:"
  marker) -> complete-linkage on token-set Jaccard >= 0.8 (conservative).

"Venezuela Earthquake Death Toll" x9 folds to one group; "...Death Toll" vs
"...Tragedy" (Jaccard 0.4) does NOT — same-event-different-wording remains the
judge's job. Complete linkage (all cross-pairs must clear the threshold) so
groups never chain transitively.

Reversible: ATLAS_UMBRELLA_LABEL_FOLD=off restores the pre-pass-free behavior.
Pure functions — no DB, no LLM — so the guardrails are unit-tested directly.
"""
from __future__ import annotations

import html
import re

# Labels that must NEVER participate in the fold: they are placeholders, not
# event descriptions — two unrelated "(label failed)" topics must not merge.
_NON_LABELS = {"", "(label failed)", "label failed", "untitled", "unknown"}

# The "Emerging: <raw headline>" marker is a lane prefix, not content — strip it
# so the marker token cannot connect unrelated emerging topics. The remaining
# raw headline still folds against an identical raw headline (correct).
_EMERGING_RE = re.compile(r"^\s*emerging\s*:\s*", re.IGNORECASE)

_TOKEN_RE = re.compile(r"[^\W\d_]+", re.UNICODE)  # letters only — digits/dates drop

# Small multilingual stopword set: connective glue only, never event-bearing.
_STOPWORDS = frozenset({
    # en
    "the", "a", "an", "of", "in", "on", "and", "for", "to", "at", "vs", "v",
    "over", "after", "amid", "as", "by", "with", "from", "into", "its",
    # es
    "el", "la", "los", "las", "de", "del", "en", "y", "por", "para", "un",
    "una", "sobre", "tras", "con", "al",
    # fr
    "le", "les", "des", "du", "et", "au", "aux", "sur",
    # pt
    "o", "os", "das", "dos", "da", "do", "e", "no", "na", "nos", "nas", "em",
    # de
    "der", "die", "das", "und", "im", "von", "zu", "mit", "den",
    # it
    "il", "lo", "gli", "delle", "nel", "nella",
})


def normalize_label_tokens(label: str | None) -> frozenset[str]:
    """Label -> the set of event-bearing tokens.

    Lowercased, HTML-entities unescaped, "Emerging:" marker stripped, tokens
    with digits dropped (dates/years/scores), stopwords dropped, single-letter
    tokens dropped. Placeholder labels return the empty set (non-participating).
    """
    if not label:
        return frozenset()
    text = html.unescape(label).strip().lower()
    if text.strip("()[]{}.:;!? ") in _NON_LABELS:
        return frozenset()
    text = _EMERGING_RE.sub("", text)
    tokens = {
        t for t in _TOKEN_RE.findall(text)
        if len(t) >= 2 and t not in _STOPWORDS
    }
    return frozenset(tokens)


def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    if inter == 0:
        return 0.0
    return inter / (len(a) + len(b) - inter)


def label_fold_groups(
    labels: list[str | None],
    *,
    threshold: float = 0.8,
    min_tokens: int = 2,
) -> dict[int, list[int]]:
    """Complete-linkage fold over normalized label token sets.

    Returns {root_index: [member_indices]} with >= 2 members each — the same
    shape the umbrella write path consumes. Conservative by construction:

    - only labels with >= ``min_tokens`` event-bearing tokens participate,
    - an edge needs Jaccard >= ``threshold`` (0.8: exact/near-exact dups only),
    - COMPLETE linkage: a group forms only when ALL cross-pairs clear the
      threshold, so near-dup groups never chain into theme megagroups.
    """
    token_sets = [normalize_label_tokens(lb) for lb in labels]
    eligible = [i for i, ts in enumerate(token_sets) if len(ts) >= min_tokens]

    edges: list[tuple[float, int, int]] = []
    for ai in range(len(eligible)):
        i = eligible[ai]
        for bi in range(ai + 1, len(eligible)):
            j = eligible[bi]
            sim = _jaccard(token_sets[i], token_sets[j])
            if sim >= threshold:
                edges.append((sim, i, j))
    edges.sort(reverse=True)

    cluster_of: dict[int, int] = {i: i for i in eligible}
    members: dict[int, list[int]] = {i: [i] for i in eligible}
    for _sim, i, j in edges:
        ci, cj = cluster_of[i], cluster_of[j]
        if ci == cj:
            continue
        mi, mj = members[ci], members[cj]
        # complete linkage: merge only if every cross-pair clears the threshold
        if all(_jaccard(token_sets[p], token_sets[q]) >= threshold
               for p in mi for q in mj):
            for p in mj:
                cluster_of[p] = ci
            mi.extend(mj)
            del members[cj]
    return {min(idxs): sorted(idxs) for idxs in members.values() if len(idxs) >= 2}


def merge_index_groups(
    n: int,
    primary: dict[int, list[int]],
    secondary: dict[int, list[int]],
) -> dict[int, list[int]]:
    """Union two {root: [indices]} groupings via union-find.

    A topic claimed by a label-fold group AND a linkage group unions the two
    (both assert same-event membership through a shared topic). Groups of >= 2,
    keyed by their minimum index — the write-path shape.
    """
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for grouping in (primary, secondary):
        for idxs in grouping.values():
            base = idxs[0]
            for other in idxs[1:]:
                parent[find(other)] = find(base)

    groups: dict[int, list[int]] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    return {min(idxs): sorted(idxs) for idxs in groups.values() if len(idxs) >= 2}
