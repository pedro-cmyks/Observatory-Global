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
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import numpy as np

from scripts.emergent_topic_identity_resolver import cosine
try:  # entry-point tolerant (-m scripts.* vs -m backend.scripts.*)
    from scripts.label_hygiene import is_placeholder_label
except ImportError:  # pragma: no cover
    from backend.scripts.label_hygiene import is_placeholder_label

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
    r"\b(stock price|share price|market movements?|market trends?|"
    r"economic and market|real estate listings?|"
    r"property listings?|company information|exchange rates?|"
    r"lottery (results?|numbers)|horoscopes?|weather forecasts?|"
    r"tv (guide|listings|program(me)? listings?)|program listings?|recipes|"
    # #229 recall-fix (2026-07-08): generic section/desk aggregates the raw-e5
    # noise gate incidentally caught. These persist forever by nature (a feed,
    # not a narrative) so they must never promote — same class as the listings
    # above. Measured on the 2026-07-08 candidate pool (TV Program Listings,
    # Joys of Joyscrolling, Economic and Market Trends).
    r"joyscrolling|joys of joy)\b",
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
    # #229 recall-fix (2026-07-08): generic country/section news aggregates that
    # sat below the recalibrated noise gate (Danish News Headlines, News Headlines
    # Cluster, Iraqi News and Culture, 'Colombia News July 2026'). A real thread
    # names its subject; 'News Headlines', 'News and Culture', '<X> News <Month>
    # <Year>' are desk digests. 'Crime Headlines' / 'Sports News' stay legit —
    # only the bare 'news headlines' grab-bag and the month-year digest match.
    r"news headlines?|news (and|&) culture|"
    r"news (january|february|march|april|may|june|july|august|september|october|november|december) 20\d\d|"
    r"tin t[ứu]c t[ổo]ng h[ợo]p|berita terkini|haber [öo]zetleri)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class LifecycleConfig:
    persist_min: int = 2        # snapshots to be promotable
    cohesion_min: float = 0.50  # mean member cohesion to promote
    volume_min: int = 30        # aggregate kept signals to promote
    # Max student evidence-role noise-rate to promote. RECALIBRATED 2026-07-08
    # (docs/state/2026-07-08-clustering-recall-fix.md): the raw-e5 student noise
    # scorer over-flags real high-cohesion narratives (Venezuela Earthquake 0.72,
    # Albanian Protests 0.80, Hezbollah 0.82) — every one of the 145 otherwise-
    # qualified candidates sat at noise>=0.50, so the old 0.50 gate promoted
    # nothing new (30 active / 868 candidate). Whitening was tested as a purity
    # replacement and DISPROVED (grab-bags like TV Listings 0.72 / Joyscrolling
    # 0.84 are topically tight; evolving stories drift low), so the honest purity
    # guard is the roundup/junk-label filter below, not a cohesion threshold. The
    # noise gate now only rejects the extreme tail; 0.85 lets real stories through
    # while TV Listings (0.98) / News Headlines Cluster (0.90) / Joyscrolling
    # (0.96) stay blocked. Reversible via --noise-max.
    noise_max: float = 0.85     # max student noise-rate to promote (quality gate)
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
    is_junk: bool = False,
    revive_to_candidate: bool = False,
    court_blocked: bool = False,
) -> str:
    """Pure state transition for one snapshot tick.

    TF-3b (2026-07-31): `revive_to_candidate` closes the exit door TF-2
    measured — a retired/deprecated topic that re-matches always lands
    `candidate` (an old topic passes the mechanical gate trivially: lifetime
    persist/volume), and a revived candidate promotes only once
    `court_blocked` is False (the label court re-certified its label against
    the CURRENT receipts). Both default off = byte-identical legacy behavior,
    including the direct resurrect.
    """
    quality_ok = noise_rate is None or noise_rate < cfg.noise_max
    # is_junk (2026-07-09 useful-coverage gate) is a content-based quality flag
    # persisted by scripts/flag_junk_topics.py (grab-bag category / listicle label
    # / few-source feed-dump). Treated like is_roundup: never promotes, demotes an
    # active topic — so junk grab-bags leave serving, not just the anchor set.
    qualifies = (
        n_snapshots >= cfg.persist_min
        and mean_cohesion >= cfg.cohesion_min
        and agg_n_signals >= cfg.volume_min
        and not is_roundup
        and not is_junk
        and quality_ok
    )
    if seen_now:
        if is_roundup or is_junk or not quality_ok:
            return "candidate"  # roundup/junk/high-noise: never promoted; demote if active
        if revive_to_candidate and state in ("deprecated", "retired"):
            return "candidate"  # v2b: revival NEVER jumps to active — court re-vets first
        if revive_to_candidate and state == "candidate" and court_blocked:
            return "candidate"  # revived, label not yet re-certified vs current receipts
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


def _qualifies(t: "Topic", cfg: LifecycleConfig) -> bool:
    """Promotion eligibility from persisted quality signals alone (no seen_now).

    Mirrors the `qualifies` clause inside next_state, but reads the topic's
    aggregate state so it can be applied to the EXISTING population during a
    gate recalibration (--regrade) without waiting for each topic to be
    re-matched by a future snapshot.
    """
    quality_ok = t.noise_rate is None or t.noise_rate < cfg.noise_max
    return (
        len(t.snapshots) >= cfg.persist_min
        and t.mean_cohesion >= cfg.cohesion_min
        and t.agg_n_signals >= cfg.volume_min
        and not t.is_roundup
        and not t.is_junk
        and quality_ok
    )


# Blob veto (2026-08-03 gate-(c) census): the label court's `entailed` stamp
# measured ~70% precise as a serving certificate — 28 judge-confirmed blob
# topics were certified AND promoted through the TF-3b gate. Promotion now
# also requires NO FRESH blob stamp (detect_overmerge stamps
# dynamic_topics.blob_confirmed_at on judge-confirmed fusions and clears it on
# re-evaluated-clean topics). The 7-day horizon is a staleness bound, not a
# pardon: the nightly sweep re-stamps a still-fused topic, so only a topic the
# sweep stopped confirming (typically membership re-formed under the same
# identity) ages out of the veto — an eternal stamp would block the identity
# long after its evidence changed.
BLOB_CONFIRMED_FRESH_DAYS = 7


def blob_confirmed_fresh(stamp: datetime | None,
                         now: datetime | None = None) -> bool:
    if stamp is None:
        return False
    return ((now or datetime.now(timezone.utc)) - stamp
            < timedelta(days=BLOB_CONFIRMED_FRESH_DAYS))


def regrade_states(topics: list[Topic], cfg: LifecycleConfig) -> tuple[int, int]:
    """Apply the current gate to the WHOLE population (gate-recalibration pass).

    next_state only reconsiders topics SEEN in the current tick, so a gate
    change (e.g. a raised noise_max) never reaches the standing candidate pool
    until each story happens to be re-matched. This one-time pass re-evaluates
    every topic against `cfg`:
      - candidate/deprecated/retired that now qualify -> active
      - active that no longer qualifies (roundup/high-noise/thin) -> candidate
    Pure state change: no member/centroid/identity mutation, no TRUNCATE, so
    resurrection identities and history are preserved (reversible = re-run with
    the prior cfg). Returns {promoted, demoted}.
    """
    promoted = demoted = 0
    for t in topics:
        ok = _qualifies(t, cfg)
        # Recency guard: only promote stories still inside the fresh window.
        # A deprecated/retired topic aged out because it went quiet (since_seen
        # >= stale_k); re-promoting it on a gate change alone would resurrect a
        # dead story (e.g. a resolved election) into serving. Candidates are new,
        # so they carry since_seen 0. This keeps --regrade to "currently-live
        # stories the old gate wrongly blocked", not "everything that ever met
        # the volume bar".
        fresh = t.since_seen < cfg.stale_k
        # TF-3b: a manual --regrade must not bypass the court gate on revived
        # stock — same condition the nightly clock applies. `newly_revived`
        # matters: --regrade runs AFTER apply_new_clusters in the same
        # invocation, and a same-pass revival has revived_at still None in
        # memory (the DB stamp lands in persist). Composed OR with the blob
        # veto: an entailed label must not promote a judge-confirmed fusion.
        court_blocked = (
            (t.revived_at is not None or t.newly_revived)
            and t.label_status != "entailed"
        ) or blob_confirmed_fresh(t.blob_confirmed_at)
        if ok and fresh and not court_blocked and t.state in ("candidate", "deprecated"):
            t.state = "active"; t.dirty = True; promoted += 1
        elif not ok and t.state == "active":
            t.state = "candidate"; t.dirty = True; demoted += 1
    return promoted, demoted


def running_mean(old: np.ndarray, k: int, new: np.ndarray) -> np.ndarray:
    """Incremental mean of k existing vectors plus one new vector."""
    return (old * k + new) / (k + 1)


# ---------- in-memory topic model (mirrors the table) ----------

class Topic:
    __slots__ = (
        "id", "identity_key", "state", "label_counts", "centroid", "anchor_centroid",
        "first_seen", "last_seen", "snapshots", "agg_n_signals", "cohesions",
        "roundup_votes", "n_labels", "since_seen", "members", "dirty", "new", "noises",
        "is_junk", "countries", "cc_snap", "revived_at", "label_status", "newly_revived",
        "blob_confirmed_at",
    )

    def __init__(self, identity_key, label, centroid, snap, n_signals, cohesion, noise=None,
                 content_roundup=False, countries=None):
        self.id: int | None = None
        self.identity_key = identity_key
        self.state = "candidate"
        # Never let a labeler-failure sentinel ("(label failed)", "(no label)")
        # become a countable label — it is truthy, so it used to win the mode
        # vote and get PERSISTED into dynamic_topics.label (Lane A, 2026-07-18).
        if is_placeholder_label(label):
            label = None
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
        # content-based junk flag; owned by scripts/flag_junk_topics.py, loaded
        # from the persisted row in hydrate. New topics start not-junk (they get
        # flagged once they carry unified-v2 members).
        self.is_junk = False
        # P2 per-country clock (2026-07-30): the country codes of the topic's
        # LATEST member snapshot — "where this topic currently lives". Same
        # definition the post-dark-door serving door uses (latest-snapshot codes,
        # ANY position; NOT the all-snapshot `top_country_codes[1]` variant that
        # counted historical membership). Empty = unattributable → ages normally.
        self.countries: set[str] = set()
        self.cc_snap: Any = None
        # TF-3b revival bookkeeping: revived_at/label_status hydrate from the
        # persisted row; newly_revived marks a revival that happened THIS pass
        # (persist stamps revived_at=NOW() + NULLs the court columns so the
        # stamp must re-certify against the topic's CURRENT receipts).
        self.revived_at: Any = None
        self.label_status: str | None = None
        self.newly_revived = False
        # Blob-veto stamp; owned by scripts/detect_overmerge.py (stamped on
        # judge-confirmed fusion, NULLed on re-evaluated-clean), loaded from
        # the persisted row in hydrate. persist() never writes it.
        self.blob_confirmed_at: Any = None
        self._note_countries(snap, countries)

    def _note_countries(self, snap, codes) -> None:
        """Record a member cluster's countries, keeping only the LATEST snapshot.

        Newer snapshot replaces; same snapshot unions (a topic can hold several
        clusters at one snapshot); older is ignored. Members are replayed in
        snapshot order in both hydrate and match paths, so this converges on the
        latest-snapshot country set either way.
        """
        codes = {str(c).strip().upper() for c in (codes or []) if str(c).strip()}
        if self.cc_snap is None or snap > self.cc_snap:
            self.cc_snap = snap
            self.countries = codes
        elif snap == self.cc_snap:
            self.countries |= codes

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
        if clabel and not is_placeholder_label(clabel):
            self.label_counts[clabel] += 1
        if is_roundup_label(clabel) or cluster.get("content_roundup"):
            self.roundup_votes += 1
        if cluster.get("noise") is not None:
            self.noises.append(float(cluster["noise"]))
        self.members.append({"cluster_id": cluster["id"], "snapshot_at": snap, "match_score": score})
        self._note_countries(snap, cluster.get("countries"))
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
        if other.cc_snap is not None:
            self._note_countries(other.cc_snap, other.countries)
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


# ── P1 (2026-07-30): ONE LIFECYCLE TICK PER PASS ────────────────────────────
# Measured defect (docs/research/recall-229/2026-07-29-threading-floor-diagnosis.md
# §2.1b): `run()` called process_snapshot once per distinct `snapshot_at` still
# holding un-ingested clusters, and EVERY such group is a full aging tick.
# Exactly one snapshot is produced per night, yet n_snapshots_processed measured
# 4,3,4,3,2,3,4 over seven runs. The extra groups are umbrella ORPHANS:
# build_umbrella_topics.py:517 DELETEs umbrella member rows every night, so the
# clusters that had attached directly to an umbrella re-enter `new_clusters` at
# their ORIGINAL snapshot_at and manufacture a tick for every topic in the world.
# With stale_k=2 / retire_m=4 one missed clustering pass then deprecates AND
# retires: 1,007 topics whose last match was 07-27 sat at since_seen=4 after a
# single elapsed snapshot, and 1,353 retired topics pass every quality bar.
#
# The fix: THE PASS IS THE CLOCK. A run advances `snapshots_since_seen` by
# exactly one regardless of how many snapshot groups it ingests; a topic matched
# in ANY group of the pass (including a re-entrant orphan group) resets to 0.
# Env-gated + reversible: ATLAS_LIFECYCLE_TICK_V2 (default OFF = legacy).
LIFECYCLE_TICK_V2_ENV = "ATLAS_LIFECYCLE_TICK_V2"
_TRUE_VALUES = {"1", "on", "true", "yes", "y"}


def lifecycle_tick_v2_enabled(env: dict[str, str] | None = None) -> bool:
    """True when the per-pass lifecycle clock is switched on. Default OFF."""
    src = os.environ if env is None else env
    return (src.get(LIFECYCLE_TICK_V2_ENV) or "").strip().lower() in _TRUE_VALUES


def use_tick_v2(rebuild: bool, env: dict[str, str] | None = None) -> bool:
    """Per-pass clock applies to INCREMENTAL runs only.

    `--rebuild` REPLAYS the whole snapshot history from an empty table, so each
    historical snapshot must still fire its own tick — collapsing all of history
    into one tick would fabricate a population that was never aged. The nightly
    runner is incremental (never --rebuild, see scripts/run-scoped-snapshot.sh
    Step 2), so this exclusion costs the fix nothing.
    """
    return lifecycle_tick_v2_enabled(env) and not rebuild


# ---------- P2: the per-country lifecycle clock ----------
#
# Measured defect (docs/research/recall-229/2026-07-29-threading-floor-diagnosis.md
# §P2): the 150-min weekday run budget DEFERS 130-154 countries every weekday
# night (0 on weekend nights), and a deferred country's topics age anyway. BO and
# ML cluster fine — 1-7 gated clusters, 100% re-match — whenever the pass reaches
# them; they die between passes. A country the budget deferred did not fail to
# produce a story: Atlas failed to look. Only 30 of 168 clustered countries can
# currently serve a thread, and 1,353 retired topics pass every quality bar.
#
# The fix: a topic ages only on passes that actually CLUSTERED one of its
# countries. No quality bar moves — persist_min, volume_min, cohesion_min,
# noise_max, roundup and junk are all untouched; only the clock is gated.
#
# WHERE THE COUNTRY LIST COMES FROM (the design choice):
# the scoped snapshot's own checkpoint file, `ck.done` (snapshot_budget.py:
# Checkpoint), written atomically after every banked country and read here.
# It is the only source that keeps the distinction P2 depends on:
#   BO deferred     -> absent from `done`        -> FROZEN (Atlas never looked)
#   MM ran, 0 kept  -> done[MM] = "no_clusters"  -> AGES (Atlas looked, honestly)
# Deriving the set from the pass's own clusters would be self-contained but
# CONFLATES those two — Myanmar (`no gated clusters` on every pass, §2.3) would
# be frozen forever, which is exactly the wrong answer. The runner already
# exports ATLAS_SNAPSHOT_STATE_DIR before invoking this script
# (scripts/run-scoped-snapshot.sh:44 -> :242), so no runner change and no new
# artifact are needed. Countries that ERRORED out are also absent from `done`
# and are therefore frozen too — same honest reason: nothing was looked at.
#
# FAIL OPEN, ALWAYS: any doubt about the country list (missing/corrupt file,
# a checkpoint describing a different snapshot than the pass being ingested,
# an empty ledger) degrades to today's behaviour — age everything — and says so
# in the summary. Freezing on a stale ledger would un-age the whole field.
# Env-gated + reversible: ATLAS_LIFECYCLE_COUNTRY_CLOCK (default OFF).
LIFECYCLE_COUNTRY_CLOCK_ENV = "ATLAS_LIFECYCLE_COUNTRY_CLOCK"
SNAPSHOT_CHECKPOINT_FILE = "scoped-snapshot-checkpoint.json"


def lifecycle_country_clock_enabled(env: dict[str, str] | None = None) -> bool:
    """True when the per-country lifecycle clock is switched on. Default OFF."""
    src = os.environ if env is None else env
    return (src.get(LIFECYCLE_COUNTRY_CLOCK_ENV) or "").strip().lower() in _TRUE_VALUES


def use_country_clock(rebuild: bool, env: dict[str, str] | None = None) -> bool:
    """Per-country clock applies to INCREMENTAL runs only.

    `--rebuild` REPLAYS the whole snapshot history from an empty table; gating
    that replay on ONE night's country ledger would freeze almost every topic in
    almost every historical tick and fabricate a population that was never aged.
    The nightly runner is incremental (see scripts/run-scoped-snapshot.sh Step 2),
    so the exclusion costs the fix nothing — same rule as the v2 tick.
    """
    return lifecycle_country_clock_enabled(env) and not rebuild


def _parse_snapshot_ts(value: Any) -> datetime | None:
    """ISO -> datetime, or None. Never raises: a bad stamp must fail open."""
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None


def clustered_countries(checkpoint: dict[str, Any] | None, *,
                        primary_snapshot: str | None) -> tuple[set[str] | None, str]:
    """Country ledger for THIS pass -> (codes | None, reason). Pure.

    None = unknown, and the caller must fail open (age everything). The ledger is
    accepted only when the checkpoint describes the very snapshot being ingested:
    `primary_snapshot` is the newest group of this run (count_passes), and the
    checkpoint's `snapshot_at` is the snapshot the R1 pass just banked. A
    mismatch means the file is stale (a crashed/skipped R1, a re-run projecting
    an older night) and freezing on it would silently stop the clock.
    """
    if not checkpoint:
        return None, "no_checkpoint"
    if primary_snapshot is None:
        return None, "no_primary_snapshot"
    ck_ts = _parse_snapshot_ts(checkpoint.get("snapshot_at"))
    pass_ts = _parse_snapshot_ts(primary_snapshot)
    if ck_ts is None or pass_ts is None:
        return None, "unparsable_snapshot"
    if (ck_ts.tzinfo is None) != (pass_ts.tzinfo is None) or ck_ts != pass_ts:
        return None, "snapshot_mismatch"
    done = checkpoint.get("done")
    if not isinstance(done, dict) or not done:
        return None, "empty_ledger"
    codes = {str(cc).strip().upper() for cc in done if str(cc).strip()}
    return (codes, "checkpoint") if codes else (None, "empty_ledger")


def load_snapshot_checkpoint(state_dir: str | None) -> dict[str, Any] | None:
    """Read the scoped snapshot's checkpoint JSON. None on anything unusual."""
    if not state_dir:
        return None
    try:
        import json as _json
        raw = _json.loads(
            (Path(state_dir) / SNAPSHOT_CHECKPOINT_FILE).read_text(encoding="utf-8"))
    except Exception:
        return None
    return raw if isinstance(raw, dict) else None


def is_frozen_country(topic: "Topic", clustered_ccs: set[str] | None) -> bool:
    """True when this pass never clustered any country this topic lives in.

    Fails open twice over: an unknown ledger (None) and an unattributable topic
    (no country on its latest member snapshot — e.g. the identity-continuity
    fallback in hydrate_topics, whose member clusters are gone) both age
    normally, exactly as today.
    """
    if clustered_ccs is None or not topic.countries:
        return False
    return not (topic.countries & clustered_ccs)


def count_passes(groups: list[tuple[str, list[dict[str, Any]]]]) -> dict[str, Any]:
    """Pass accounting for the v2 clock (the ORPHAN GUARD's reporting half).

    `groups` is group_by_snapshot() output — sorted ascending, so the LAST group
    is the current pass's primary (newest) snapshot and every earlier group is a
    RE-ENTRANT: clusters returning at a snapshot_at older than this pass. They
    are members of the current pass, never additional passes. Under the v2 clock
    they can no longer fire extra aging ticks (advance_states runs once per run),
    so the guard's remaining independent job is to stop them being REPORTED as
    processed snapshots — n_snapshots_processed is the TF-1 verification metric.
    """
    if not groups:
        return {"passes": 0, "groups": 0, "reentrant_groups": 0, "primary_snapshot": None}
    primary = groups[-1][0]
    return {
        "passes": 1,
        "groups": len(groups),
        "reentrant_groups": sum(1 for snap, _ in groups if snap < primary),
        "primary_snapshot": primary,
    }


def match_snapshot(topics: list[Topic], snap_clusters: list[dict[str, Any]], snap) -> set[int]:
    """Match/attach one snapshot group's clusters. NO aging.

    Returns the indices of topics SEEN in this group (matched or newly founded).
    Indices are stable across groups within a run because topics are only ever
    appended. Matching reads centroids only — never `state` or `since_seen` — so
    deferring the aging step cannot change which cluster attaches where.
    """
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
                countries=c.get("countries"),
            )
            # constructor seeds aggregates from this cluster; record its member row
            t.members.append({"cluster_id": c["id"], "snapshot_at": snap, "match_score": 1.0})
            topics.append(t)
            seen_topics.add(len(topics) - 1)
    return seen_topics


def advance_states(topics: list[Topic], seen_topics: set[int], cfg: LifecycleConfig,
                   clustered_ccs: set[str] | None = None,
                   revive_to_candidate: bool = False) -> int:
    """Advance every topic's lifecycle clock by EXACTLY ONE tick.

    `seen_topics` = indices matched/founded during this tick. Under the v2 clock
    the caller passes the union over the whole pass, so a topic matched in any
    group (primary or re-entrant orphan) resets to 0 exactly as today.

    `clustered_ccs` (P2, None = off/unknown) = the countries this pass actually
    clustered. An UNSEEN topic none of whose countries were clustered is skipped
    whole: neither the counter nor the state moves, because this pass did not
    happen for it. Skipping the transition too is not a shortcut — for an unseen
    topic `next_state` can only ever demote on `since_seen`, so evaluating it on
    a frozen counter would be aging a topic on a pass that never looked.
    SEEN topics are untouched by P2: they reset to 0 exactly as today, so a
    ledger error can never hold a matched topic back.

    Returns the number of topics frozen by the country clock (0 when off).
    """
    frozen = 0
    for ti, t in enumerate(topics):
        seen = ti in seen_topics
        if not seen and is_frozen_country(t, clustered_ccs):
            frozen += 1
            continue
        t.since_seen = 0 if seen else t.since_seen + 1
        # TF-3b: a revived candidate stays blocked until the court re-certifies
        # its label against the current receipts. `newly_revived` counts too so
        # the block is airtight within the same in-memory run. Composed OR with
        # the blob veto (gate-(c) census): court `entailed` alone measured ~70%
        # precise as a serving certificate, so an entailed label must not
        # promote a topic the overmerge judge freshly confirmed as a fusion.
        court_blocked = (
            (t.revived_at is not None or t.newly_revived)
            and t.label_status != "entailed"
        ) or blob_confirmed_fresh(t.blob_confirmed_at)
        was_state = t.state
        new_state = next_state(
            t.state, seen_now=seen, n_snapshots=len(t.snapshots),
            mean_cohesion=t.mean_cohesion, agg_n_signals=t.agg_n_signals,
            is_roundup=t.is_roundup, since_seen=t.since_seen, cfg=cfg,
            noise_rate=t.noise_rate, is_junk=t.is_junk,
            revive_to_candidate=revive_to_candidate, court_blocked=court_blocked,
        )
        if new_state != t.state:
            if (revive_to_candidate and seen and new_state == "candidate"
                    and was_state in ("deprecated", "retired")):
                t.newly_revived = True
            t.state = new_state
            t.dirty = True
    return frozen


def process_snapshot(topics: list[Topic], snap_clusters: list[dict[str, Any]], snap,
                     cfg: LifecycleConfig,
                     clustered_ccs: set[str] | None = None,
                     report: dict[str, Any] | None = None) -> list[Topic]:
    """Match a snapshot's clusters, then advance every topic's state one tick.

    Legacy per-snapshot-group unit of work — unchanged; still the whole story
    when ATLAS_LIFECYCLE_TICK_V2 is off, and the per-historical-snapshot unit
    under --rebuild. `clustered_ccs` (default None = off) is the P2 country
    ledger, orthogonal to which tick regime is in force; `report` accumulates
    the frozen-tick count across calls.
    """
    frozen = advance_states(topics, match_snapshot(topics, snap_clusters, snap), cfg,
                            clustered_ccs)
    if report is not None:
        report["frozen"] = int(report.get("frozen", 0)) + frozen
    return topics


def apply_new_clusters(
    topics: list[Topic],
    groups: list[tuple[str, list[dict[str, Any]]]],
    cfg: LifecycleConfig,
    *,
    tick_v2: bool,
    clustered_ccs: set[str] | None = None,
    report: dict[str, Any] | None = None,
) -> int:
    """Ingest every un-ingested snapshot group; return the number of ticks fired.

    tick_v2 OFF (default): one tick per group — byte-identical to the historical
    loop, including the phantom ticks the orphan cycle manufactures.
    tick_v2 ON: match all groups first, then age ONCE. The pass is the clock.

    `clustered_ccs` (P2, default None = off) composes with either regime: the
    ledger describes what the RUN clustered, so every tick the run fires — one
    under v2, one per group under legacy — is gated by the same country set.
    `report` collects "frozen" (topic-ticks skipped by the country clock).
    """
    if report is not None:
        report.setdefault("frozen", 0)
    if not tick_v2:
        ticks = 0
        for snap, snap_clusters in groups:
            process_snapshot(topics, snap_clusters, snap, cfg, clustered_ccs, report)
            ticks += 1
        return ticks
    if not groups:
        return 0
    seen_all: set[int] = set()
    for snap, snap_clusters in groups:
        seen_all |= match_snapshot(topics, snap_clusters, snap)
    # TF-3b rides ONLY the v2 clock: revival-to-candidate + court-gated
    # promotion are part of the tick_v2 regime (flag off = legacy everything,
    # including the direct resurrect TF-2 measured).
    frozen = advance_states(topics, seen_all, cfg, clustered_ccs,
                            revive_to_candidate=True)
    if report is not None:
        report["frozen"] = int(report.get("frozen", 0)) + frozen
        report["revived_to_candidate"] = sum(1 for t in topics if t.newly_revived)
    return 1


# ---------- DB ----------

# Bounded `id = ANY($1)` fetches (2026-07-19). ONE unbatched ANY() over every
# sample_signal_id exceeded statement_timeout ('600s') under post-snapshot
# contention and killed the WHOLE projection — the 07-12/13 "dynamic_topics
# projection failed (non-fatal)" incidents left serving a night behind while
# the snapshot itself was fresh. Same medicine as the writer's keyset
# pagination: no single statement may approach the timeout.
ID_FETCH_CHUNK = int(os.environ.get("ATLAS_PROJECT_ID_FETCH_CHUNK", "10000") or "10000")


def chunk_ids(ids: list[int], size: int = 10_000) -> list[list[int]]:
    """Split an id list into bounded slices for `= ANY($1)` statements.

    Pure + order-preserving; size<=0 returns ONE unbatched chunk (explicit
    legacy opt-out via ATLAS_PROJECT_ID_FETCH_CHUNK=0)."""
    ids = list(ids)
    if not ids:
        return []
    if size <= 0:
        return [ids]
    return [ids[i:i + size] for i in range(0, len(ids), size)]


async def _fetch_by_ids(conn, sql: str, all_ids: list[int]):
    """Run an `= ANY($1::bigint[])` query in bounded chunks; one row list."""
    rows: list = []
    for chunk in chunk_ids(all_ids, ID_FETCH_CHUNK):
        rows.extend(await conn.fetch(sql, chunk))
    return rows


async def load_clusters(conn) -> list[dict[str, Any]]:
    rows = await conn.fetch(
        "SELECT id, snapshot_at, cluster_id, label, n_signals, cohesion, "
        "sample_signal_ids, centroid_vec, role_noise_rate, top_country_codes "
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
            # P2 per-country clock: which countries this cluster's signals sit in.
            "countries": [str(x) for x in (r["top_country_codes"] or [])],
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
    rows = await _fetch_by_ids(
        conn,
        "SELECT id, headline, source_name FROM signals_v2 WHERE id = ANY($1::bigint[])",
        all_ids)
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
    rows = await _fetch_by_ids(
        conn,
        "SELECT id, headline FROM signals_v2 WHERE id = ANY($1::bigint[])",
        all_ids)
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
        "SELECT id, identity_key, state, snapshots_since_seen, label, "
        "centroid_vec, first_seen, last_seen, n_snapshots, agg_n_signals, "
        "mean_cohesion, noise_rate, is_junk, is_umbrella, revived_at, "
        "label_status, blob_confirmed_at FROM dynamic_topics"
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
        # Umbrellas are DERIVED aggregates (build_umbrella_topics): their member
        # rows are cleared + rebuilt from children every night, so a cluster that
        # attaches directly to one never founds its own identity and loses its
        # membership at the next rebuild — then re-attaches on re-adoption, a
        # permanent swallow cycle (72 orphaned clusters incl. a 70-signal
        # fragment, 2026-07-28). They must never be matching targets here.
        if tr["is_umbrella"]:
            continue
        mem = members.get(int(tr["id"]), [])
        mem = [m for m in mem if m["cluster_id"] in clusters_by_id]
        if not mem:
            # IDENTITY-CONTINUITY FIX (2026-07-04 universe-collapse incident):
            # when a topic's member clusters are gone from emergent_clusters
            # (retention trim / substrate wipe), the old code SKIPPED the
            # topic entirely — it never entered the in-memory list, so the
            # next snapshot's clusters could not centroid-match it and
            # re-founded the same story under a new identity. Fall back to
            # the PERSISTED dynamic_topics state instead: the running
            # centroid_vec doubles as the anchor (approximation — the true
            # founding anchor is unrecoverable once members are gone, and
            # the last known position is the honest bound for what the
            # topic may absorb).
            if tr["centroid_vec"] is None:
                continue
            t = Topic(
                identity_key=tr["identity_key"], label=tr["label"] or "",
                centroid=tr["centroid_vec"],
                snap=tr["last_seen"].isoformat() if tr["last_seen"] else "",
                n_signals=int(tr["agg_n_signals"] or 0),
                cohesion=tr["mean_cohesion"], noise=tr["noise_rate"],
            )
            if tr["first_seen"]:
                t.first_seen = tr["first_seen"].isoformat()
            # preserve the persisted snapshot count so a later touch does
            # not collapse n_snapshots to 1 (synthetic keys, never real
            # snapshot ids, so they cannot collide with attach()).
            n_snaps = max(1, int(tr["n_snapshots"] or 1))
            t.snapshots = {f"restored:{i}" for i in range(n_snaps - 1)}
            t.snapshots.add(t.last_seen or "restored:last")
            t.id = int(tr["id"])
            t.state = tr["state"]
            t.since_seen = int(tr["snapshots_since_seen"] or 0)
            t.is_junk = bool(tr["is_junk"])
            t.revived_at = tr["revived_at"]
            t.label_status = tr["label_status"]
            t.blob_confirmed_at = tr["blob_confirmed_at"]
            t.new = False
            t.members = []
            t.dirty = False
            topics.append(t)
            continue
        mem.sort(key=lambda m: m["snapshot_at"])
        first = clusters_by_id[mem[0]["cluster_id"]]
        t = Topic(
            identity_key=tr["identity_key"], label=first["label"], centroid=first["centroid"],
            snap=mem[0]["snapshot_at"], n_signals=first["n_signals"],
            cohesion=first.get("cohesion"), noise=first.get("noise"),
            content_roundup=bool(first.get("content_roundup")),
            countries=first.get("countries"),
        )
        t.members.append({"cluster_id": first["id"], "snapshot_at": mem[0]["snapshot_at"], "match_score": 1.0})
        for m in mem[1:]:
            c = clusters_by_id[m["cluster_id"]]
            t.attach(c, m["snapshot_at"], 1.0)
        t.id = int(tr["id"])
        t.state = tr["state"]
        t.since_seen = int(tr["snapshots_since_seen"] or 0)
        t.is_junk = bool(tr["is_junk"])
        t.revived_at = tr["revived_at"]
        t.label_status = tr["label_status"]
        t.blob_confirmed_at = tr["blob_confirmed_at"]
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
                t.identity_key, t.state, t.label or None, [float(x) for x in t.centroid],
                first_seen, last_seen, len(t.snapshots), t.agg_n_signals,
                cohesion, t.is_roundup, t.since_seen, t.noise_rate,
            )
            if row:
                t.id = int(row["id"])
                t.new = False
                written["inserted"] += 1
        else:
            # label=COALESCE(...): a run whose member labels are all placeholders
            # projects label=None — keep the previously persisted real label
            # rather than downgrading it to NULL (Lane A never-persist rule).
            # TF-3b revival rides the SAME statement ($12) — atomic by
            # construction. Two autocommit statements over the WAN pooler was
            # the half-written-snapshot failure class: state='candidate'
            # landing WITHOUT the court-column reset would let a stale
            # `entailed` from the topic's former life promote it next tick.
            # In one statement either both land or neither does; the old stamp
            # can never certify the NEW receipts.
            await conn.execute(
                "UPDATE dynamic_topics SET state=$2, label=COALESCE($3, label), centroid_vec=$4, "
                "last_seen=$5::timestamptz, n_snapshots=$6, agg_n_signals=$7, mean_cohesion=$8, "
                "is_roundup=$9, snapshots_since_seen=$10, noise_rate=$11, updated_at=NOW(), "
                "last_state_change=CASE WHEN state IS DISTINCT FROM $2 THEN NOW() ELSE last_state_change END, "
                "revived_at=CASE WHEN $12 THEN NOW() ELSE revived_at END, "
                "label_status=CASE WHEN $12 THEN NULL ELSE label_status END, "
                "label_checked_at=CASE WHEN $12 THEN NULL ELSE label_checked_at END, "
                "label_court_model=CASE WHEN $12 THEN NULL ELSE label_court_model END, "
                "label_proposed=CASE WHEN $12 THEN NULL ELSE label_proposed END "
                "WHERE id=$1",
                t.id, t.state, t.label or None, [float(x) for x in t.centroid], last_seen,
                len(t.snapshots), t.agg_n_signals, cohesion, t.is_roundup, t.since_seen,
                t.noise_rate, t.newly_revived,
            )
            written["updated"] += 1
            if t.newly_revived:
                t.newly_revived = False
                written["revived"] = written.get("revived", 0) + 1
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
    if getattr(args, "noise_max", None) is not None:
        overrides["noise_max"] = args.noise_max
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
        groups = group_by_snapshot(new_clusters)
        tick_v2 = use_tick_v2(bool(args.rebuild))
        # P2: the country ledger for THIS pass (None = off or unusable = age all).
        country_clock = use_country_clock(bool(args.rebuild))
        clustered_ccs: set[str] | None = None
        cc_reason = "off"
        if country_clock:
            clustered_ccs, cc_reason = clustered_countries(
                load_snapshot_checkpoint(getattr(args, "snapshot_state_dir", None)),
                primary_snapshot=(groups[-1][0] if groups else None),
            )
        clock_report: dict[str, Any] = {}
        processed_snaps = apply_new_clusters(topics, groups, cfg, tick_v2=tick_v2,
                                             clustered_ccs=clustered_ccs,
                                             report=clock_report)

        merges = 0
        if args.rebuild:
            before_merge = len(topics)
            topics = merge_duplicates(topics)
            merges = before_merge - len(topics)

        regraded: tuple[int, int] | None = None
        if getattr(args, "regrade", False):
            regraded = regrade_states(topics, cfg)

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
            "noise_max": cfg.noise_max,
            "dry_run": args.dry_run,
        }
        if tick_v2:
            # Reported ONLY under the v2 clock so the legacy summary stays
            # byte-identical. `n_snapshots_processed` is now a PASS count (the
            # TF-1 metric); the group/re-entrant split is the orphan ledger.
            acct = count_passes(groups)
            summary["lifecycle_tick_v2"] = True
            summary["n_snapshot_groups"] = acct["groups"]
            summary["n_reentrant_groups"] = acct["reentrant_groups"]
            summary["primary_snapshot"] = acct["primary_snapshot"]
            # TF-3b gate-(b) receipt — visible in dry-run too (persist's
            # written["revived"] only exists on write passes).
            summary["revived_to_candidate"] = int(
                clock_report.get("revived_to_candidate", 0))
        if country_clock:
            # Reported ONLY under the country clock so the legacy summary stays
            # byte-identical. `country_clock_source` is the honesty field: it
            # says "checkpoint" when the ledger was accepted and names the
            # fail-open reason when it was not (aging then = today's behaviour).
            summary["lifecycle_country_clock"] = True
            summary["country_clock_source"] = cc_reason
            summary["n_clustered_countries"] = (
                len(clustered_ccs) if clustered_ccs is not None else None)
            summary["n_frozen_topic_ticks"] = int(clock_report.get("frozen", 0))
        if regraded is not None:
            summary["regrade_promoted"], summary["regrade_demoted"] = regraded
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
    ap.add_argument("--noise-max", type=float, default=None,
                    help="override LifecycleConfig.noise_max (max student noise-rate to promote; 2026-07-08 recal=0.85)")
    ap.add_argument("--snapshot-state-dir",
                    default=os.environ.get("ATLAS_SNAPSHOT_STATE_DIR"),
                    help="dir holding the scoped snapshot's checkpoint "
                         "(scoped-snapshot-checkpoint.json) — the country ledger the "
                         "P2 per-country clock reads. Defaults to ATLAS_SNAPSHOT_STATE_DIR, "
                         "which run-scoped-snapshot.sh already exports. Ignored unless "
                         "ATLAS_LIFECYCLE_COUNTRY_CLOCK is on; unusable = fail open.")
    ap.add_argument("--regrade", action="store_true",
                    help="one-time gate recalibration: re-evaluate the WHOLE standing population "
                         "against the current gate (promote qualified candidates/deprecated even if "
                         "not seen this tick, demote active that no longer qualifies). No TRUNCATE.")
    return ap.parse_args()


def main() -> None:
    import json
    args = parse_args()
    summary = asyncio.run(run(args))
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
