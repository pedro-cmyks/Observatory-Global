#!/usr/bin/env python3
"""Project emergent_clusters into the dynamic_topics lifecycle (Phase 6, Sub-A).

Incremental, idempotent writer. Processes emergent_clusters snapshots in
time order; for each not-yet-ingested snapshot it matches each cluster to
the best existing dynamic_topic by centroid cosine (>= MATCH_THRESHOLD,
greedy 1-to-1). Matched clusters attach (running-mean centroid, member
row, last_seen, aggregates); unmatched clusters open a new `candidate`
topic. After each snapshot tick, state transitions run on every topic
using quality signals — not persistence alone — so roundup/incoherent
identities never get promoted.

Runs in SHADOW: writes only dynamic_topics / dynamic_topic_members,
which no product surface reads yet. Use --dry-run to compute without
writing.

Run on the off-iCloud ML/numpy venv with DATABASE_URL:
  /Users/pedro/AtlasLocalWorker/atlasvenv/bin/python -m scripts.project_dynamic_topics
"""

from __future__ import annotations

import argparse
import asyncio
import os
import re
from collections import Counter
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

import numpy as np

from scripts.emergent_topic_identity_resolver import cosine

MATCH_THRESHOLD = 0.88
# Anchor guard (#224, measured 2026-06-11): a cluster must also match the
# topic's ORIGINAL (first-cluster) centroid, not only the running mean. The
# running mean drifts toward a generic news centroid over ~20 snapshots,
# after which everything matches >= 0.85 and the topic becomes a black hole
# ('PSG Victory Riots' absorbed Orwell/Modi/earthquakes at 0.87-0.93 running
# but only 0.785-0.879 vs anchor; genuine Russia-Ukraine continuations sit
# at 0.92-0.97 vs anchor). 0.90 separated those populations, but same-domain
# conflation survived it (a fresh PSG topic absorbed 'Real Madrid Offers 150M'
# at 0.903 and 'Mundial 2026' at 0.931 — football↔football runs hot). 0.93
# keeps the measured genuine cores (Russia-Ukraine 0.94-0.97) and cuts the
# domain-cousin tail. Residual same-domain conflation above 0.93 is a known
# limitation; the proper fix is an entity-overlap check (#224 follow-up).
ANCHOR_THRESHOLD = 0.93
# NOTE (#224): a label-instability guard was tried and removed — genuine
# evolving stories (Russia-Ukraine) legitimately get a fresh DeepSeek label
# per snapshot, so label diversity over-fires. Semantic coherence is already
# enforced structurally by the anchor guard on attach.
# Recurring-format noise (#224): coherent-looking labels that are listings,
# not narratives. They persist forever by nature, so they must never promote.
LISTING_PATTERNS = re.compile(
    r"\b(stock price|share price|market movements?|real estate listings?|"
    r"property listings?|company information|exchange rates?|"
    r"lottery (results?|numbers)|horoscopes?|weather forecasts?|"
    r"tv (guide|listings)|recipes)\b",
    re.IGNORECASE,
)
# Deliberately narrow: only unambiguous grab-bag markers. Broad terms like
# "headlines" or "digest" catch legitimate topics ("Crime Headlines") and
# were validated out. Label-regex is a weak first filter; the robust quality
# gates are the evidence-role noise rate and the instability guard above.
# Multilingual markers added 2026-06-11 (#224): 'Noticias Regionales
# Variadas' was active and unflagged because the patterns were English-only.
ROUNDUP_PATTERNS = re.compile(
    r"\b(round\s?up|mixed news|miscellaneous|assorted|news brief|"
    r"various (news|stories|topics|updates)|grab\s?bag|"
    r"noticias (variadas|varias|mixtas|diversas|regionales variadas|generales)|"
    r"resumen de noticias|vari(as|os) noticias|noticias del d[ií]a|"
    r"actualit[eé]s? diverses|nachrichten[üu]berblick|"
    r"notizie varie|not[íi]cias (variadas|diversas)|"
    # #224 (2026-06-23): non-English / generic grab-bags that promoted from the
    # persisted-corpus snapshot. 'Notícias Diversas', 'Regional News and Events'.
    r"diverse news|(regional|general|local) news( (and|&) (events|updates|stories))?|"
    r"news (and|&) events|"
    r"tin t[ứu]c t[ổo]ng h[ợo]p|berita terkini|haber [öo]zetleri)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class LifecycleConfig:
    persist_min: int = 2        # snapshots to be promotable
    cohesion_min: float = 0.50  # mean member cohesion to promote
    volume_min: int = 30        # aggregate kept signals to promote
    noise_max: float = 0.50     # max student noise-rate to promote (quality gate)
    stale_k: int = 2            # active -> deprecated after K unseen ticks
    retire_m: int = 4           # deprecated -> retired after M unseen ticks


def is_roundup_label(label: str | None) -> bool:
    if not label:
        return False
    return bool(ROUNDUP_PATTERNS.search(label)) or bool(LISTING_PATTERNS.search(label))


# Content-entropy roundup detection (#224): language-agnostic. A real narrative
# thread shares a subject — some content token recurs across most member
# headlines (an entity/event: "Starmer", "Clive Davis", "Delhi"). A grab-bag
# roundup does not — every headline is a different topic, so no token recurs.
# This catches multilingual roundups the label regex can't enumerate.
import html as _html  # noqa: E402

# Generic tokens that recur in headlines WITHOUT indicating a shared subject:
# news/date/format words across the languages we ingest. Kept compact; the
# metric is robust to a few leaks because it takes the SINGLE most-shared token.
_GENERIC_TOKENS = {
    # english
    "news", "live", "update", "updates", "latest", "today", "report", "reports",
    "day", "daily", "the", "and", "for", "with", "from", "after", "over", "amid",
    "say", "says", "new", "top", "watch", "video", "photos",
    # date words
    "june", "juni", "junio", "junho", "haziran", "2026", "2025",
    # spanish / portuguese
    "las", "los", "del", "que", "con", "por", "para", "una", "noticias", "notícias",
    "hoy", "dia", "día", "nesta", "esta",
    # vietnamese generic
    "tin", "tức", "tổng", "hợp", "hôm", "nay", "giá", "thị", "trường",
    # indonesian
    "berita", "ini", "yang", "dan", "untuk", "dari", "juni", "selasa", "daftar",
    # turkish
    "haber", "için", "ile", "son", "dakika",
    # french / german
    "les", "des", "une", "pour", "avec", "der", "die", "das", "und", "für",
}


def _subject_tokens(headline: str) -> set[str]:
    """Letter-only tokens (len>=3), HTML-unescaped, minus generic/news/date words."""
    text = _html.unescape(headline or "").lower()
    toks = re.findall(r"[^\W\d_]{3,}", text, re.UNICODE)
    return {t for t in toks if t not in _GENERIC_TOKENS}


def subject_concentration(headlines: list[str]) -> float | None:
    """Max share of member headlines that contain any single content token.

    ~1.0 = a clear shared subject (real thread); low = grab-bag (roundup).
    Returns None when undecidable: too few headlines, or a no-whitespace script
    (CJK) where this word-level metric does not apply.
    """
    heads = [h for h in headlines if h and h.strip()]
    n = len(heads)
    if n < 6:
        return None
    token_sets = [_subject_tokens(h) for h in heads]
    avg_tokens = sum(len(s) for s in token_sets) / n
    if avg_tokens < 1.5:  # CJK / no-whitespace: word metric inapplicable
        return None
    df: Counter = Counter()
    for s in token_sets:
        df.update(s)
    if not df:
        return None
    return max(df.values()) / n


def source_concentration(sources: list[str]) -> float:
    """Share of members from the single most common outlet (0=many, 1=one)."""
    s = [x for x in sources if x]
    if not s:
        return 0.0
    return Counter(s).most_common(1)[0][1] / len(s)


# A grab-bag roundup has BOTH (a) no shared subject across headlines AND (b) is
# dominated by a SINGLE outlet — it is that outlet's daily-digest feed dumped as
# one cluster. The source guard is essential: a broad REAL thread (Ukraine war,
# a market crash) also has dispersed headlines, but it spans MANY outlets, so it
# must not be flagged. Calibrated on the 2026-06-23 snapshot — cleanly separates
# Regional/Tin Tức/Notícias Diversas (0.12-0.21 subj, 0.38-0.54 src) from
# Ukraine War / Stock Market Crash (0.21-0.25 subj but only 0.17-0.21 src).
SUBJECT_CONCENTRATION_MIN = 0.30
SOURCE_DOMINANCE_MIN = 0.35
# A single outlet's wire feed dumped as one cluster (#214 follow-up, 2026-06-24):
# every headline carries the outlet's boilerplate prefix ("Côte d'Ivoire-AIP/ …"),
# so a geo/outlet slug token recurs in EVERY headline and fakes a perfect subject
# concentration — the dump escaped the guard above and even got a hallucinated
# DeepSeek label ('Russian Shadow Fleet Interceptions' over 546 aip.ci members).
# When one outlet owns the cluster this completely, strip the shared leading
# prefix and re-test: a real single-outlet story keeps a shared subject (Delhi
# fire: "fire"/"kills" still recur); a feed dump collapses to no shared subject.
# When one outlet owns this much of a cluster at scale it is that outlet's feed
# dumped as a topic, not a corroborated narrative — flag regardless of how
# coherent its single-outlet "subject" looks. The subject metric alone cannot
# catch these: a wire feed prefixes every headline with its own geo/outlet slug
# ("Côte d'Ivoire-AIP/ …", "Côte d'Ivoire-AIP /", "Côte d'Ivoire-AIP/Inter/"),
# so a slug token recurs in every headline and fakes subject concentration 1.0.
# That is exactly how aip.ci dumped 546 headlines into one cluster that drew the
# hallucinated label 'Russian Shadow Fleet Interceptions' (#214, 2026-06-24).
SINGLE_OUTLET_DUMP_MIN = 0.90
SINGLE_OUTLET_DUMP_MIN_MEMBERS = 6


def is_roundup_by_content(headlines: list[str], sources: list[str]) -> bool:
    src = source_concentration(sources)
    real_sources = [s for s in sources if s]
    # Single-outlet wire-dump: Atlas treats a narrative as corroborated only when
    # more than one outlet carries it, so near-total single-outlet ownership at
    # scale is a feed dump by construction. Well above the calibrated multi-outlet
    # roundup band (0.38-0.54) so genuine broad/narrow threads are untouched.
    if len(real_sources) >= SINGLE_OUTLET_DUMP_MIN_MEMBERS and src >= SINGLE_OUTLET_DUMP_MIN:
        return True
    conc = subject_concentration(headlines)
    if conc is None or conc >= SUBJECT_CONCENTRATION_MIN:
        return False
    # dispersed subject across members: a roundup only if one outlet also dominates.
    return src >= SOURCE_DOMINANCE_MIN


def next_state(
    state: str,
    *,
    seen_now: bool,
    n_snapshots: int,
    mean_cohesion: float,
    agg_n_signals: int,
    is_roundup: bool,
    since_seen: int,
    cfg: LifecycleConfig,
    noise_rate: float | None = None,
) -> str:
    """Pure state transition for one snapshot tick."""
    quality_ok = noise_rate is None or noise_rate < cfg.noise_max
    qualifies = (
        n_snapshots >= cfg.persist_min
        and mean_cohesion >= cfg.cohesion_min
        and agg_n_signals >= cfg.volume_min
        and not is_roundup
        and quality_ok
    )
    if seen_now:
        if is_roundup or not quality_ok:
            return "candidate"  # roundup or high-noise: never promoted; demote if active
        if qualifies:
            return "active"
        if state in ("deprecated", "retired"):
            return "candidate"  # re-opened / resurrected as provisional
        return state
    # not seen this tick
    if state == "active" and since_seen >= cfg.stale_k:
        return "deprecated"
    if state == "deprecated" and since_seen >= cfg.retire_m:
        return "retired"
    return state


def running_mean(old: np.ndarray, k: int, new: np.ndarray) -> np.ndarray:
    """Incremental mean of k existing vectors plus one new vector."""
    return (old * k + new) / (k + 1)


# ---------- in-memory topic model (mirrors the table) ----------

class Topic:
    __slots__ = (
        "id", "identity_key", "state", "label_counts", "centroid", "anchor_centroid",
        "first_seen", "last_seen", "snapshots", "agg_n_signals", "cohesions",
        "roundup_votes", "n_labels", "since_seen", "members", "dirty", "new", "noises",
    )

    def __init__(self, identity_key, label, centroid, snap, n_signals, cohesion, noise=None,
                 content_roundup=False):
        self.id: int | None = None
        self.identity_key = identity_key
        self.state = "candidate"
        self.label_counts: Any = Counter({label: 1}) if label else Counter()
        self.centroid = np.array(centroid, dtype=np.float64)
        # immutable identity anchor (#224): the first cluster's centroid.
        # attach() never updates it, so drift in the running mean cannot
        # widen what the topic is allowed to absorb.
        self.anchor_centroid = np.array(centroid, dtype=np.float64)
        self.first_seen = snap
        self.last_seen = snap
        self.snapshots = {snap}
        self.agg_n_signals = int(n_signals)
        self.cohesions = [float(cohesion)] if cohesion is not None else []
        self.noises = [float(noise)] if noise is not None else []
        self.roundup_votes = 1 if (is_roundup_label(label) or content_roundup) else 0
        self.n_labels = 1
        self.since_seen = 0
        self.members: list[dict[str, Any]] = []
        self.dirty = True
        self.new = True

    @property
    def n_member_clusters(self) -> int:
        return len(self.members)

    @property
    def mean_cohesion(self) -> float:
        return float(np.mean(self.cohesions)) if self.cohesions else 0.0

    @property
    def is_roundup(self) -> bool:
        # the topic's representative (mode) label is the identity signal; a
        # grab-bag label ("X News Roundup") marks the topic regardless of the
        # noisier per-member vote. Vote kept as a secondary OR.
        return is_roundup_label(self.label) or (
            self.n_labels > 0 and self.roundup_votes * 2 >= self.n_labels
        )

    @property
    def label(self) -> str:
        return self.label_counts.most_common(1)[0][0] if self.label_counts else ""

    @property
    def noise_rate(self) -> float | None:
        return round(float(np.mean(self.noises)), 4) if self.noises else None

    def attach(self, cluster: dict[str, Any], snap, score: float) -> None:
        self.centroid = running_mean(self.centroid, self.n_member_clusters, np.array(cluster["centroid"]))
        self.last_seen = max(self.last_seen, snap)
        self.snapshots.add(snap)
        self.agg_n_signals += int(cluster["n_signals"])
        if cluster.get("cohesion") is not None:
            self.cohesions.append(float(cluster["cohesion"]))
        self.n_labels += 1
        clabel = cluster.get("label")
        if clabel:
            self.label_counts[clabel] += 1
        if is_roundup_label(clabel) or cluster.get("content_roundup"):
            self.roundup_votes += 1
        if cluster.get("noise") is not None:
            self.noises.append(float(cluster["noise"]))
        self.members.append({"cluster_id": cluster["id"], "snapshot_at": snap, "match_score": score})
        self.dirty = True

    def absorb(self, other: "Topic") -> None:
        """Merge another near-duplicate topic into this identity."""
        old_members = self.n_member_clusters
        other_members = other.n_member_clusters
        if old_members + other_members:
            self.centroid = (
                (self.centroid * old_members + other.centroid * other_members)
                / max(old_members + other_members, 1)
            )
        self.first_seen = min(self.first_seen, other.first_seen)
        self.last_seen = max(self.last_seen, other.last_seen)
        self.snapshots.update(other.snapshots)
        self.agg_n_signals += other.agg_n_signals
        self.cohesions.extend(other.cohesions)
        self.noises.extend(other.noises)
        self.roundup_votes += other.roundup_votes
        self.n_labels += other.n_labels
        self.label_counts.update(other.label_counts)
        self.since_seen = min(self.since_seen, other.since_seen)
        if self.state != "active" and other.state == "active":
            self.state = "active"
        self.members.extend(other.members)
        self.dirty = True


MERGE_THRESHOLD = 0.90  # stricter than linking; label guard prevents broad vector-chain collapse
MERGE_LABEL_MIN = 0.80


def labels_compatible(a: str | None, b: str | None) -> bool:
    """Return true when labels are close enough to be the same user topic."""
    if not a or not b:
        return False
    norm_a = re.sub(r"[^a-z0-9]+", " ", a.lower()).strip()
    norm_b = re.sub(r"[^a-z0-9]+", " ", b.lower()).strip()
    if not norm_a or not norm_b:
        return False
    if norm_a == norm_b:
        return True
    return SequenceMatcher(None, norm_a, norm_b).ratio() >= MERGE_LABEL_MIN


def merge_duplicates(topics: list[Topic], threshold: float = MERGE_THRESHOLD) -> list[Topic]:
    """Merge topics whose centroids and labels are both near-duplicates.

    The older identity (earlier first_seen) survives and absorbs the other.
    Roundups are excluded so broad grab-bag identities cannot bridge otherwise
    distinct topics through dense centroid neighborhoods.
    """
    merged = True
    while merged:
        merged = False
        n = len(topics)
        for i in range(n):
            for j in range(i + 1, n):
                left, right = topics[i], topics[j]
                if left.is_roundup or right.is_roundup:
                    continue
                if not labels_compatible(left.label, right.label):
                    continue
                if cosine(left.centroid, right.centroid) >= threshold:
                    if left.first_seen <= right.first_seen:
                        survivor, victim = left, right
                    else:
                        survivor, victim = right, left
                    survivor.absorb(victim)
                    topics.remove(victim)
                    merged = True
                    break
            if merged:
                break
    return topics


def process_snapshot(topics: list[Topic], snap_clusters: list[dict[str, Any]], snap, cfg: LifecycleConfig) -> list[Topic]:
    """Match a snapshot's clusters, then advance every topic's state one tick."""
    # greedy 1-to-1 match by centroid cosine
    pairs = []
    for ci, c in enumerate(snap_clusters):
        for ti, t in enumerate(topics):
            s = cosine(np.array(c["centroid"]), t.centroid)
            if s >= MATCH_THRESHOLD and (
                cosine(np.array(c["centroid"]), t.anchor_centroid) >= ANCHOR_THRESHOLD
            ):
                pairs.append((s, ci, ti))
    pairs.sort(reverse=True)
    used_c: set[int] = set()
    used_t: set[int] = set()
    seen_topics: set[int] = set()
    for s, ci, ti in pairs:
        if ci in used_c or ti in used_t:
            continue
        used_c.add(ci)
        used_t.add(ti)
        topics[ti].attach(snap_clusters[ci], snap, s)
        seen_topics.add(ti)
    for ci, c in enumerate(snap_clusters):
        if ci not in used_c:
            t = Topic(
                identity_key=f"dyn-{c['snapshot_at']}-{c['cluster_id']}",
                label=c["label"], centroid=c["centroid"], snap=snap,
                n_signals=c["n_signals"], cohesion=c.get("cohesion"), noise=c.get("noise"),
                content_roundup=bool(c.get("content_roundup")),
            )
            # constructor seeds aggregates from this cluster; record its member row
            t.members.append({"cluster_id": c["id"], "snapshot_at": snap, "match_score": 1.0})
            topics.append(t)
            seen_topics.add(len(topics) - 1)

    # advance state for every topic
    for ti, t in enumerate(topics):
        seen = ti in seen_topics
        t.since_seen = 0 if seen else t.since_seen + 1
        new_state = next_state(
            t.state, seen_now=seen, n_snapshots=len(t.snapshots),
            mean_cohesion=t.mean_cohesion, agg_n_signals=t.agg_n_signals,
            is_roundup=t.is_roundup, since_seen=t.since_seen, cfg=cfg,
            noise_rate=t.noise_rate,
        )
        if new_state != t.state:
            t.state = new_state
            t.dirty = True
    return topics


# ---------- DB ----------

async def load_clusters(conn) -> list[dict[str, Any]]:
    rows = await conn.fetch(
        "SELECT id, snapshot_at, cluster_id, label, n_signals, cohesion, "
        "sample_signal_ids, centroid_vec, role_noise_rate "
        "FROM emergent_clusters WHERE centroid_vec IS NOT NULL ORDER BY snapshot_at, cluster_id"
    )
    return [
        {
            "id": int(r["id"]), "snapshot_at": r["snapshot_at"].isoformat(),
            "cluster_id": r["cluster_id"], "label": r["label"],
            "n_signals": int(r["n_signals"] or 0),
            "cohesion": float(r["cohesion"]) if r["cohesion"] is not None else None,
            "sample_signal_ids": [int(x) for x in (r["sample_signal_ids"] or [])],
            "centroid": np.array(r["centroid_vec"], dtype=np.float64),
            # cached per-cluster noise ($0: computed once, never recomputed)
            "noise": float(r["role_noise_rate"]) if r["role_noise_rate"] is not None else None,
        }
        for r in rows
    ]


async def flag_content_roundups(conn, clusters: list[dict[str, Any]]) -> None:
    """Set cluster['content_roundup'] (#224, content-entropy detection).

    A grab-bag = no shared subject across headlines AND single-outlet dominated
    (a daily-digest feed dumped as one cluster). Pure string metric, no torch.
    Language-agnostic where headlines are whitespace-segmented.
    """
    # Only the newest snapshot's clusters need flagging — older ones already
    # settled into topics. Bounds the headline fetch.
    if not clusters:
        return
    latest = max(c["snapshot_at"] for c in clusters)
    todo = [c for c in clusters
            if c["snapshot_at"] == latest and "content_roundup" not in c
            and c.get("sample_signal_ids")]
    if not todo:
        return
    all_ids = sorted({sid for c in todo for sid in c["sample_signal_ids"]})
    rows = await conn.fetch(
        "SELECT id, headline, source_name FROM signals_v2 WHERE id = ANY($1::bigint[])", all_ids)
    info = {int(r["id"]): (r["headline"] or "", r["source_name"] or "") for r in rows}
    for c in todo:
        ids = c["sample_signal_ids"]
        heads = [info[s][0] for s in ids if s in info]
        srcs = [info[s][1] for s in ids if s in info]
        c["content_roundup"] = is_roundup_by_content(heads, srcs)


async def score_clusters_noise(conn, clusters: list[dict[str, Any]], model_path: str) -> None:
    """Attach per-cluster evidence-role noise fraction (in place).

    Embeds each cluster's sample headlines with e5, runs the local student,
    and sets cluster['noise'] = fraction predicted 'noise'. Needs torch.
    """
    import json
    from scripts.score_assignments_gate import _build_embedder
    from scripts.bridge_gate_student_scope import _student_predict

    # only score clusters with no cached noise -> bounded, $0 API, never recomputed
    todo = [c for c in clusters if c.get("noise") is None]
    if not todo:
        return
    model = json.loads(open(model_path, encoding="utf-8").read())
    all_ids = sorted({sid for c in todo for sid in c["sample_signal_ids"]})
    if not all_ids:
        return
    rows = await conn.fetch(
        "SELECT id, headline FROM signals_v2 WHERE id = ANY($1::bigint[])", all_ids
    )
    headline = {int(r["id"]): (r["headline"] or "").strip() for r in rows}

    embed, _ = _build_embedder(model["embedding_model"])
    for c in todo:
        texts = [headline.get(sid, "") for sid in c["sample_signal_ids"] if headline.get(sid)]
        if not texts:
            continue
        head_emb = embed([f"query: {t}" for t in texts])
        label_emb = embed([f"query: {(c['label'] or '').strip()}"] * len(texts))
        roles, _ = _student_predict(model, head_emb, label_emb)
        c["noise"] = round(sum(1 for r in roles if r == "noise") / len(roles), 4)
        await conn.execute(
            "UPDATE emergent_clusters SET role_noise_rate=$2 WHERE id=$1", c["id"], c["noise"]
        )


async def ingested_cluster_ids(conn) -> set[int]:
    rows = await conn.fetch("SELECT emergent_cluster_id FROM dynamic_topic_members")
    return {int(r["emergent_cluster_id"]) for r in rows}


async def hydrate_topics(conn, clusters_by_id: dict[int, dict[str, Any]]) -> tuple[list[Topic], set[int]]:
    """Rebuild in-memory topics from the DB by replaying their members.

    Replaying through Topic+attach reconstructs centroid/aggregates exactly,
    so the incremental run starts from true state without persisting Counters.
    """
    trows = await conn.fetch(
        "SELECT id, identity_key, state, snapshots_since_seen FROM dynamic_topics"
    )
    mrows = await conn.fetch(
        "SELECT dynamic_topic_id, emergent_cluster_id, snapshot_at "
        "FROM dynamic_topic_members ORDER BY snapshot_at"
    )
    members: dict[int, list[dict[str, Any]]] = {}
    done: set[int] = set()
    for m in mrows:
        cid = int(m["emergent_cluster_id"])
        done.add(cid)
        members.setdefault(int(m["dynamic_topic_id"]), []).append(
            {"cluster_id": cid, "snapshot_at": m["snapshot_at"].isoformat()}
        )

    topics: list[Topic] = []
    for tr in trows:
        mem = members.get(int(tr["id"]), [])
        mem = [m for m in mem if m["cluster_id"] in clusters_by_id]
        if not mem:
            continue
        mem.sort(key=lambda m: m["snapshot_at"])
        first = clusters_by_id[mem[0]["cluster_id"]]
        t = Topic(
            identity_key=tr["identity_key"], label=first["label"], centroid=first["centroid"],
            snap=mem[0]["snapshot_at"], n_signals=first["n_signals"],
            cohesion=first.get("cohesion"), noise=first.get("noise"),
            content_roundup=bool(first.get("content_roundup")),
        )
        t.members.append({"cluster_id": first["id"], "snapshot_at": mem[0]["snapshot_at"], "match_score": 1.0})
        for m in mem[1:]:
            c = clusters_by_id[m["cluster_id"]]
            t.attach(c, m["snapshot_at"], 1.0)
        t.id = int(tr["id"])
        t.state = tr["state"]
        t.since_seen = int(tr["snapshots_since_seen"] or 0)
        t.new = False
        t.members = []   # already persisted
        t.dirty = False  # only re-persist if touched this run
        topics.append(t)
    return topics, done


def group_by_snapshot(clusters: list[dict[str, Any]]) -> list[tuple[str, list[dict[str, Any]]]]:
    snaps: dict[str, list[dict[str, Any]]] = {}
    for c in clusters:
        snaps.setdefault(c["snapshot_at"], []).append(c)
    return sorted(snaps.items())


async def persist(conn, topics: list[Topic]) -> dict[str, int]:
    from datetime import datetime

    def _ts(v):
        return datetime.fromisoformat(v) if isinstance(v, str) else v

    written = {"inserted": 0, "updated": 0, "members": 0}
    for t in topics:
        if not t.dirty:
            continue
        cohesion = t.mean_cohesion if t.cohesions else None
        first_seen, last_seen = _ts(t.first_seen), _ts(t.last_seen)
        if t.new and t.id is None:
            row = await conn.fetchrow(
                "INSERT INTO dynamic_topics (identity_key, state, label, centroid_vec, "
                "first_seen, last_seen, n_snapshots, agg_n_signals, mean_cohesion, "
                "is_roundup, snapshots_since_seen, noise_rate, last_state_change) "
                "VALUES ($1,$2,$3,$4,$5::timestamptz,$6::timestamptz,$7,$8,$9,$10,$11,$12,NOW()) "
                "ON CONFLICT (identity_key) DO NOTHING RETURNING id",
                t.identity_key, t.state, t.label, [float(x) for x in t.centroid],
                first_seen, last_seen, len(t.snapshots), t.agg_n_signals,
                cohesion, t.is_roundup, t.since_seen, t.noise_rate,
            )
            if row:
                t.id = int(row["id"])
                t.new = False
                written["inserted"] += 1
        else:
            await conn.execute(
                "UPDATE dynamic_topics SET state=$2, label=$3, centroid_vec=$4, "
                "last_seen=$5::timestamptz, n_snapshots=$6, agg_n_signals=$7, mean_cohesion=$8, "
                "is_roundup=$9, snapshots_since_seen=$10, noise_rate=$11, updated_at=NOW(), "
                "last_state_change=CASE WHEN state IS DISTINCT FROM $2 THEN NOW() ELSE last_state_change END "
                "WHERE id=$1",
                t.id, t.state, t.label, [float(x) for x in t.centroid], last_seen,
                len(t.snapshots), t.agg_n_signals, cohesion, t.is_roundup, t.since_seen,
                t.noise_rate,
            )
            written["updated"] += 1
        if t.id is not None:
            for m in t.members:
                res = await conn.execute(
                    "INSERT INTO dynamic_topic_members (dynamic_topic_id, emergent_cluster_id, "
                    "snapshot_at, match_score) VALUES ($1,$2,$3::timestamptz,$4) "
                    "ON CONFLICT (dynamic_topic_id, emergent_cluster_id) DO NOTHING",
                    t.id, m["cluster_id"], _ts(m["snapshot_at"]), m["match_score"],
                )
                if res.endswith("1"):
                    written["members"] += 1
            t.members = []
        t.dirty = False
    return written


async def run(args: argparse.Namespace) -> dict[str, Any]:
    import asyncpg

    db = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not db:
        raise SystemExit("DATABASE_URL required")
    # Gate overrides (reversible — defaults unchanged). The scoped-clustering regime
    # (#229 R1) produces tight regional topics of 8-30 signals at ~0.97 cohesion; the
    # default volume_min=30 is calibrated for the old global regime (100s-of-signal
    # threads) and starves them. --volume-min recalibrates for scoped; --persist-min 1
    # is the one-time bootstrap so the first scoped snapshot can promote (normally 2).
    overrides: dict[str, Any] = {}
    if getattr(args, "persist_min", None) is not None:
        overrides["persist_min"] = args.persist_min
    if getattr(args, "volume_min", None) is not None:
        overrides["volume_min"] = args.volume_min
    cfg = LifecycleConfig(**overrides)
    conn = await asyncpg.connect(db)
    try:
        clusters = await load_clusters(conn)
        await flag_content_roundups(conn, clusters)   # #224 content-entropy roundup flag
        if args.student_model:
            await score_clusters_noise(conn, clusters, args.student_model)

        if args.rebuild:
            topics: list[Topic] = []
            done: set[int] = set()
        else:
            clusters_by_id = {c["id"]: c for c in clusters}
            topics, done = await hydrate_topics(conn, clusters_by_id)

        # only snapshots with at least one not-yet-ingested cluster are new
        new_clusters = [c for c in clusters if c["id"] not in done]
        processed_snaps = 0
        for snap, snap_clusters in group_by_snapshot(new_clusters):
            process_snapshot(topics, snap_clusters, snap, cfg)
            processed_snaps += 1

        merges = 0
        if args.rebuild:
            before_merge = len(topics)
            topics = merge_duplicates(topics)
            merges = before_merge - len(topics)

        summary: dict[str, Any] = {
            "mode": "rebuild" if args.rebuild else "incremental",
            "n_clusters": len(clusters),
            "n_new_clusters": len(new_clusters),
            "n_snapshots_processed": processed_snaps,
            "n_topics": len(topics),
            "n_merged_topics": merges,
            "by_state": _state_counts(topics),
            "roundups": sum(1 for t in topics if t.is_roundup),
            "high_noise": sum(1 for t in topics if (t.noise_rate or 0) >= cfg.noise_max),
            "scored_noise": args.student_model is not None,
            "dry_run": args.dry_run,
        }
        if not args.dry_run:
            if args.rebuild:
                await conn.execute("TRUNCATE dynamic_topic_members, dynamic_topics RESTART IDENTITY CASCADE")
            summary["written"] = await persist(conn, topics)
        return summary
    finally:
        await conn.close()


def _state_counts(topics: list[Topic]) -> dict[str, int]:
    out: dict[str, int] = {}
    for t in topics:
        out[t.state] = out.get(t.state, 0) + 1
    return out


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Project emergent_clusters into dynamic_topics (shadow).")
    ap.add_argument("--dry-run", action="store_true", help="compute without writing")
    ap.add_argument("--rebuild", action="store_true", help="rebuild from all snapshots (TRUNCATE first)")
    ap.add_argument("--student-model", help="path to evidence-role student json for the noise quality gate")
    ap.add_argument("--persist-min", type=int, default=None,
                    help="override LifecycleConfig.persist_min (snapshots-seen to promote; scoped bootstrap uses 1)")
    ap.add_argument("--volume-min", type=int, default=None,
                    help="override LifecycleConfig.volume_min (min agg kept signals to promote; scoped regime ~12)")
    return ap.parse_args()


def main() -> None:
    import json
    args = parse_args()
    summary = asyncio.run(run(args))
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
