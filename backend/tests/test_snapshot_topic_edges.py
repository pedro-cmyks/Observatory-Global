"""Track C1 — the edge-snapshot STORE (spec docs/superpowers/specs/
2026-07-21-time-axis-versioned-relationships.md §6).

Freezes:
  (a) topic_edge_snapshots rows are keyed on `identity_key`, not the ephemeral
      topic id — canonicalized identity_key_a <= identity_key_b.
  (b) the writer's upserts are idempotent (re-running converges, no growth).
  (c) the entity backbone is rarity-gated: a ubiquitous entity scores thin
      and gets squeezed out under a cap; a genuinely rare pair scores strong
      and survives.
  (d) edges where either side's identity_key is null/missing are skipped,
      never written with a fabricated key, and the skip is counted honestly.

No real DB: the pure math (`app.services.topic_edge_snapshot`) is tested with
synthetic in-memory vectors/dicts; the writer I/O (`scripts.snapshot_topic_
edges`) is tested against a fake asyncpg-shaped connection (mirrors the
`FakeLoadConn` pattern in test_narrative_lineage.py). The one exception is
`test_run_end_to_end_...`, which loads the REAL whitening asset (it ships in
the repo, `app/data/e5_whitening.npz` — same as test_dossier_walk.py) to
prove the full fetch -> whiten -> compute -> upsert wiring, still with a fake
connection standing in for the database.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import numpy as np
import pytest

from app.services.topic_edge_snapshot import (
    BackboneRow,
    EdgeRow,
    compute_backbone_rows,
    compute_edge_rows,
)
from scripts import snapshot_topic_edges as ste


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------- fixtures
def _unit_vecs(n: int, dim: int = 8, seed: int = 3) -> np.ndarray:
    """Small already-unit-norm synthetic vectors — `compute_edge_rows` takes
    pre-whitened input, so pure tests never need the real whitening asset or
    768 dims."""
    rng = np.random.default_rng(seed)
    v = rng.standard_normal((n, dim)).astype(np.float32)
    v = v / np.linalg.norm(v, axis=1, keepdims=True)
    return v


def _clustered_vecs(dim: int = 8, seed: int = 11) -> np.ndarray:
    """4 vectors: [0]=base, [1]=near [0] (mutual close neighbor), [2]=also
    near [0]/[1] (the null-identity node), [3]=orthogonal-ish orphan — so the
    kNN graph (k>=3 over n=4) connects everyone, letting a single test cover
    both kept and skipped edges."""
    rng = np.random.default_rng(seed)
    base = rng.standard_normal(dim).astype(np.float32)
    near1 = base + 0.05 * rng.standard_normal(dim).astype(np.float32)
    near2 = base + 0.06 * rng.standard_normal(dim).astype(np.float32)
    orphan = rng.standard_normal(dim).astype(np.float32)
    m = np.stack([base, near1, near2, orphan])
    return m / np.linalg.norm(m, axis=1, keepdims=True)


# ---------------------------------------------------------------- (a) keyed on identity_key
class TestEdgesKeyedOnIdentityKey:
    def test_rows_carry_identity_keys_not_topic_ids(self):
        vecs = _clustered_vecs()
        topic_ids = ["dynamic-topic-201", "dynamic-topic-202",
                     "dynamic-topic-203", "dynamic-topic-204"]
        identity_keys = ["id-201", "id-202", "id-203", "id-204"]
        rows, skipped = compute_edge_rows(topic_ids, identity_keys, vecs, k=3)
        assert skipped == 0
        assert rows, "expected at least one edge over 4 mutually-close nodes"
        id_set = set(identity_keys)
        for r in rows:
            assert isinstance(r, EdgeRow)
            # the join key is identity_key — every row's a/b must be real
            # identity keys, and topic_id_a/b is carried only for reference.
            assert r.identity_key_a in id_set and r.identity_key_b in id_set
            assert r.topic_id_a in topic_ids and r.topic_id_b in topic_ids
            # canonical ordering so an unordered pair is never stored twice
            assert r.identity_key_a <= r.identity_key_b
            # whitened cosine is NOT clamped to [0,1] — a weak top-k pick can
            # legitimately read low/negative (see migration 089 comment).
            assert -1.0 <= r.weight <= 1.0
            assert r.degree == 1          # C1 persists only the direct graph
            assert r.basis == "semantic"

    def test_no_duplicate_pairs_even_when_knn_is_mutual(self):
        # base/near1 are each other's nearest neighbor (mutual) — must still
        # appear as exactly ONE canonicalized row, not two directed ones.
        vecs = _clustered_vecs()
        topic_ids = ["dynamic-topic-1", "dynamic-topic-2",
                     "dynamic-topic-3", "dynamic-topic-4"]
        identity_keys = ["k1", "k2", "k3", "k4"]
        rows, _ = compute_edge_rows(topic_ids, identity_keys, vecs, k=3)
        pairs = [(r.identity_key_a, r.identity_key_b) for r in rows]
        assert len(pairs) == len(set(pairs))

    def test_pure_and_deterministic(self):
        vecs = _clustered_vecs()
        topic_ids = ["dynamic-topic-1", "dynamic-topic-2",
                     "dynamic-topic-3", "dynamic-topic-4"]
        identity_keys = ["k1", "k2", "k3", "k4"]
        r1, s1 = compute_edge_rows(topic_ids, identity_keys, vecs, k=3)
        r2, s2 = compute_edge_rows(topic_ids, identity_keys, vecs, k=3)
        assert r1 == r2 and s1 == s2

    def test_mismatched_lengths_raise(self):
        with pytest.raises(ValueError):
            compute_edge_rows(["a", "b"], ["k1"], _unit_vecs(2), k=1)


# ---------------------------------------------------------------- (d) null identity skipped
class TestNullIdentitySkipped:
    def test_null_identity_edges_omitted_and_counted(self):
        vecs = _clustered_vecs()
        topic_ids = ["dynamic-topic-201", "dynamic-topic-202",
                     "dynamic-topic-203", "dynamic-topic-204"]
        # node index 2 (near2) has NO identity_key — a topic that hasn't
        # resolved one (defensive case; dynamic_topics.identity_key is
        # NOT NULL in schema, but the writer must never fabricate a key).
        identity_keys = ["id-201", "id-202", None, "id-204"]
        rows, skipped = compute_edge_rows(topic_ids, identity_keys, vecs, k=3)
        assert skipped > 0, "expected at least one skipped edge touching the null-identity node"
        touched_null_topic = {r.topic_id_a for r in rows} | {r.topic_id_b for r in rows}
        assert "dynamic-topic-203" not in touched_null_topic
        for r in rows:
            assert r.identity_key_a is not None and r.identity_key_b is not None

    def test_all_null_identities_yields_no_rows(self):
        vecs = _unit_vecs(3)
        topic_ids = ["dynamic-topic-1", "dynamic-topic-2", "dynamic-topic-3"]
        rows, skipped = compute_edge_rows(topic_ids, [None, None, None], vecs, k=2)
        assert rows == []
        assert skipped > 0


# ---------------------------------------------------------------- (c) rarity-gated backbone
class TestBackboneRarityGate:
    def _scenario(self):
        """`trump` co-occurs with a DIFFERENT rare partner in 10 topics
        (df(trump)=10, each partner df=1) — the classic #234 ubiquitous-actor
        risk. `aleph`/`bet` co-occur together in exactly 2 topics and nowhere
        else (df=2 each) — a genuinely rare, distinctive pair."""
        topic_entities: dict[str, list[str]] = {}
        for i in range(10):
            topic_entities[f"t-trump-{i}"] = ["trump", f"partner{i}"]
        topic_entities["t-rare-1"] = ["aleph", "bet"]
        topic_entities["t-rare-2"] = ["aleph", "bet"]
        return topic_entities

    def test_ubiquitous_entity_scores_thin_rare_pair_scores_strong(self):
        rows, meta = compute_backbone_rows(self._scenario())
        by_pair = {(r.entity_a, r.entity_b): r for r in rows}
        trump_rows = [r for (a, b), r in by_pair.items() if "trump" in (a, b)]
        rare_row = by_pair[("aleph", "bet")]
        assert trump_rows, "expected trump-partner edges in the backbone"
        for tr in trump_rows:
            assert tr.rarity_weight < rare_row.rarity_weight
            # trump's own df equals df_max -> norm_rarity(trump)=0 -> the MIN
            # side pins the weight at the formula's floor (0.30), regardless
            # of how rare the one-off partner is.
            assert tr.rarity_weight == pytest.approx(0.30, abs=1e-6)
        assert rare_row.rarity_weight > 0.5
        assert rare_row.cooccur_count == 2
        assert meta["entities"] >= 12
        assert meta["df_max"] == 10

    def test_capped_to_max_edges_keeps_the_strongest(self):
        rows, meta = compute_backbone_rows(self._scenario(), max_edges=1)
        assert len(rows) == 1
        assert (rows[0].entity_a, rows[0].entity_b) == ("aleph", "bet")
        assert meta["pairs_kept"] == 1
        assert meta["pairs_considered"] > 1

    def test_top_k_per_topic_bounds_fanout(self):
        # 20 persons in ONE topic; only the top_k_per_topic=8 most-frequent
        # (i.e. the first 8, since the caller supplies frequency order)
        # participate in ANY pair.
        many = [f"person{i}" for i in range(20)]
        rows, meta = compute_backbone_rows({"t-many": many}, top_k_per_topic=8)
        touched = {a for r in rows for a in (r.entity_a, r.entity_b)}
        assert touched == set(many[:8])
        assert meta["entities"] == 8

    def test_min_cooccur_filters_singletons(self):
        rows, _ = compute_backbone_rows(
            {"t1": ["a", "b"], "t2": ["a", "c"]}, min_cooccur=2)
        assert rows == []  # every pair here co-occurs only once

    def test_canonical_ordering(self):
        rows, _ = compute_backbone_rows({"t1": ["zeta", "alpha"]})
        assert rows[0].entity_a == "alpha" and rows[0].entity_b == "zeta"


# ---------------------------------------------------------------- (b) idempotent upsert
class _FakeWriteConn:
    """Emulates the upsert identity for BOTH tables — a keyed store per kind,
    mirroring `FakeLoadConn` in test_narrative_lineage.py."""

    def __init__(self):
        self.edge_store: dict[tuple, tuple] = {}
        self.backbone_store: dict[tuple, tuple] = {}
        self.executemany_calls = 0

    async def executemany(self, sql, rows):
        assert "ON CONFLICT" in sql
        self.executemany_calls += 1
        if "topic_edge_snapshots" in sql:
            for r in rows:
                self.edge_store[(r[0], r[1], r[2])] = r   # snapshot_at, ik_a, ik_b
        elif "entity_backbone_edges" in sql:
            for r in rows:
                self.backbone_store[(r[1], r[2], r[3])] = r  # window_end, entity_a, entity_b
        else:
            raise AssertionError(f"unexpected executemany target: {sql[:60]}")

    async def execute(self, *a, **k):
        return None


class TestIdempotentUpsert:
    def test_edge_upsert_converges_on_rerun(self):
        conn = _FakeWriteConn()
        snapshot_at = datetime(2026, 7, 21, tzinfo=timezone.utc)
        rows = [
            EdgeRow(identity_key_a="id-1", identity_key_b="id-2",
                    topic_id_a="dynamic-topic-1", topic_id_b="dynamic-topic-2",
                    degree=1, weight=0.71, basis="semantic"),
            EdgeRow(identity_key_a="id-1", identity_key_b="id-3",
                    topic_id_a="dynamic-topic-1", topic_id_b="dynamic-topic-3",
                    degree=1, weight=0.42, basis="semantic"),
        ]
        n1 = _run(ste.write_edges(conn, snapshot_at, rows))
        first = dict(conn.edge_store)
        n2 = _run(ste.write_edges(conn, snapshot_at, rows))
        assert n1 == n2 == 2
        assert conn.edge_store == first
        assert len(conn.edge_store) == 2   # no duplication across the re-run

    def test_edge_upsert_updates_weight_in_place(self):
        conn = _FakeWriteConn()
        snapshot_at = datetime(2026, 7, 21, tzinfo=timezone.utc)
        row_v1 = EdgeRow(identity_key_a="id-1", identity_key_b="id-2",
                         topic_id_a="dynamic-topic-1", topic_id_b="dynamic-topic-2",
                         degree=1, weight=0.50, basis="semantic")
        row_v2 = EdgeRow(identity_key_a="id-1", identity_key_b="id-2",
                         topic_id_a="dynamic-topic-1", topic_id_b="dynamic-topic-2",
                         degree=1, weight=0.66, basis="semantic")
        _run(ste.write_edges(conn, snapshot_at, [row_v1]))
        _run(ste.write_edges(conn, snapshot_at, [row_v2]))
        assert len(conn.edge_store) == 1
        stored = conn.edge_store[(snapshot_at, "id-1", "id-2")]
        assert stored[6] == pytest.approx(0.66)   # weight column, updated in place

    def test_backbone_upsert_converges_on_rerun(self):
        conn = _FakeWriteConn()
        ws = datetime(2026, 6, 21, tzinfo=timezone.utc)
        we = datetime(2026, 7, 21, tzinfo=timezone.utc)
        rows = [BackboneRow(entity_a="aleph", entity_b="bet",
                            cooccur_count=2, rarity_weight=0.6)]
        n1 = _run(ste.write_backbone(conn, ws, we, rows))
        first = dict(conn.backbone_store)
        n2 = _run(ste.write_backbone(conn, ws, we, rows))
        assert n1 == n2 == 1
        assert conn.backbone_store == first
        assert len(conn.backbone_store) == 1


# ---------------------------------------------------------------- run() end-to-end (fake conn)
class _FakeRunConn:
    """A fake connection that answers `fetch` by which SQL the writer sends —
    the same discrimination trick test_dossier_walk.py's `_FakeConn` uses,
    extended to two distinct queries + the write path."""

    def __init__(self, topic_rows, entity_rows):
        self._topic_rows = topic_rows
        self._entity_rows = entity_rows
        self.edge_store: dict[tuple, tuple] = {}
        self.backbone_store: dict[tuple, tuple] = {}

    async def execute(self, *a, **k):
        return None

    async def fetch(self, sql, *args):
        if "FROM dynamic_topics" in sql:
            return self._topic_rows
        if "FROM topic_members" in sql:
            return self._entity_rows
        return []

    async def executemany(self, sql, rows):
        assert "ON CONFLICT" in sql
        if "topic_edge_snapshots" in sql:
            for r in rows:
                self.edge_store[(r[0], r[1], r[2])] = r
        elif "entity_backbone_edges" in sql:
            for r in rows:
                self.backbone_store[(r[1], r[2], r[3])] = r


def _topic_row(tid: int, identity_key, vec: np.ndarray) -> dict:
    return {"id": tid, "identity_key": identity_key,
            "centroid_vec": [float(x) for x in vec]}


def _real_whitened_dim_vecs():
    """768-dim vectors so the REAL whitening asset (app/data/e5_whitening.npz)
    applies cleanly — mirrors test_dossier_walk.py's `_rows()` fixture."""
    rng = np.random.default_rng(7)
    base = rng.standard_normal(768).astype(np.float32)
    near = base + 0.05 * rng.standard_normal(768).astype(np.float32)
    near_no_identity = base + 0.06 * rng.standard_normal(768).astype(np.float32)
    orphan = rng.standard_normal(768).astype(np.float32)
    return base, near, near_no_identity, orphan


class TestRunEndToEnd:
    def test_run_end_to_end_with_fake_conn_and_real_whitening(self):
        base, near, near_no_id, orphan = _real_whitened_dim_vecs()
        topic_rows = [
            _topic_row(301, "id-301", base),
            _topic_row(302, "id-302", near),
            _topic_row(303, None, near_no_id),      # unresolved identity_key
            _topic_row(304, "id-304", orphan),
        ]
        entity_rows = [
            {"topic_id": "dynamic-topic-301", "persons": ["donald trump", "javier milei"]},
            {"topic_id": "dynamic-topic-302", "persons": ["donald trump", "gustavo petro"]},
        ]
        conn = _FakeRunConn(topic_rows, entity_rows)
        snapshot_at = datetime(2026, 7, 21, 12, 0, tzinfo=timezone.utc)

        summary = _run(ste.run(conn, snapshot_at=snapshot_at, window_hours=720))

        assert summary["topics_seen"] == 4
        assert summary["edges_skipped_null_identity"] >= 1   # node 303 has no identity_key
        # every written edge is keyed on real identity_key strings, never
        # "dynamic-topic-303" or any topic id.
        for (snap, a, b) in conn.edge_store:
            assert snap == snapshot_at
            assert a in {"id-301", "id-302", "id-304"}
            assert b in {"id-301", "id-302", "id-304"}
        assert summary["edges_written"] == len(conn.edge_store)
        # backbone: trump co-occurs with milei once and with petro once ->
        # both pairs share the ubiquitous 'donald trump' side.
        assert summary["backbone_written"] == len(conn.backbone_store)
        assert conn.backbone_store  # non-empty given the entity_rows above

        # idempotent re-run: same snapshot_at converges, no growth.
        first_edges = dict(conn.edge_store)
        first_backbone = dict(conn.backbone_store)
        _run(ste.run(conn, snapshot_at=snapshot_at, window_hours=720))
        assert conn.edge_store == first_edges
        assert conn.backbone_store == first_backbone

    def test_run_dry_run_writes_nothing(self):
        base, near, _near_no_id, orphan = _real_whitened_dim_vecs()
        topic_rows = [
            _topic_row(401, "id-401", base),
            _topic_row(402, "id-402", near),
            _topic_row(403, "id-403", orphan),
        ]
        conn = _FakeRunConn(topic_rows, [])
        summary = _run(ste.run(conn, dry_run=True))
        assert conn.edge_store == {} and conn.backbone_store == {}
        assert summary["dry_run"] is True
        # dry-run still reports honest counts of what WOULD have been written
        assert summary["topics_seen"] == 3
