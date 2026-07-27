"""Refresh mode (`--reembed-ids`) must be able to CORRECT a stored embedding,
while the default incremental path must still refuse to.

That contrast is the point of the whole feature. The default path is what keeps
the nightly cron cheap and idempotent (write once, never rewrite); refresh mode
is the only way a vector whose source headline changed can ever be repaired.
If either half drifts — the default starts overwriting, or refresh stops
overwriting — the guarantee is gone in a way nothing else would catch.
"""
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.embed_hot_corpus import (
    _read_reembed_ids,
    _load_reembed_cursor,
    _save_reembed_cursor,
    _cosine,
    _reembed,
)

SCRIPT = Path(__file__).parents[1] / "scripts/embed_hot_corpus.py"


# --------------------------------------------------------------------------
# the contrast
# --------------------------------------------------------------------------

def test_default_path_never_overwrites_but_refresh_mode_does():
    source = SCRIPT.read_text()

    # The default incremental INSERT keeps DO NOTHING...
    default_insert = source[source.index("_INSERT = "):source.index("# Parallel writes")]
    assert "ON CONFLICT (signal_id) DO NOTHING" in default_insert
    assert "DO UPDATE" not in default_insert

    # ...and only refresh mode upgrades to DO UPDATE.
    upsert = source[source.index("_REEMBED_UPSERT = "):source.index("def _cosine")]
    assert "ON CONFLICT (signal_id) DO UPDATE" in upsert
    assert "SET vec = EXCLUDED.vec" in upsert
    assert "embedded_at = now()" in upsert


def test_default_selector_still_skips_rows_that_already_have_an_embedding():
    # The reason a stale vector is unreachable by the default path at all.
    assert "AND e.signal_id IS NULL" in SCRIPT.read_text()


def test_refresh_returns_before_the_retention_sweep():
    # A repair must never delete vectors on its way through.
    source = SCRIPT.read_text()
    branch = source.index("if args.reembed_ids:")
    sweep = source.index("DELETE FROM signal_embeddings WHERE embedded_at")
    assert branch < sweep


# --------------------------------------------------------------------------
# id-list reading: bounded, resumable, and loud about bad input
# --------------------------------------------------------------------------

def test_reads_bare_ids_and_backfill_ledgers_the_same_way(tmp_path):
    bare = tmp_path / "ids.txt"
    bare.write_text("# comment\n30\n10\n\n20\n10\n")
    assert _read_reembed_ids(bare, after_id=0, limit=100) == [10, 20, 30]

    # exactly the shape scripts/backfill_decode_headlines.py emits
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text("".join(
        json.dumps({"id": i, "before": "a&#xA3;", "after": "a£"}) + "\n"
        for i in (7, 5, 9)
    ))
    assert _read_reembed_ids(ledger, after_id=0, limit=100) == [5, 7, 9]


def test_after_id_and_limit_bound_the_run(tmp_path):
    p = tmp_path / "ids.txt"
    p.write_text("\n".join(str(i) for i in range(1, 11)))
    assert _read_reembed_ids(p, after_id=4, limit=3) == [5, 6, 7]
    assert _read_reembed_ids(p, after_id=10, limit=3) == []


def test_a_malformed_line_stops_the_run_instead_of_silently_shrinking_it(tmp_path):
    p = tmp_path / "ids.txt"
    p.write_text("1\nnot-an-id\n3\n")
    with pytest.raises(SystemExit):
        _read_reembed_ids(p, after_id=0, limit=100)


def test_cursor_round_trips_and_defaults_to_zero(tmp_path):
    p = tmp_path / "ids.txt"
    p.write_text("1\n")
    assert _load_reembed_cursor(p) == 0
    _save_reembed_cursor(p, 4242)
    assert _load_reembed_cursor(p) == 4242


# --------------------------------------------------------------------------
# end-to-end flow against a fake connection
# --------------------------------------------------------------------------

class _FakeConn:
    def __init__(self, rows):
        self._rows = rows
        self.executed = []

    async def fetch(self, sql, chunk):
        return [r for r in self._rows if r["id"] in set(chunk)]

    async def execute(self, sql, *a):
        self.executed.append((sql, a))

    def transaction(self):
        conn = self

        class _T:
            async def __aenter__(self_):
                return None

            async def __aexit__(self_, *e):
                return False
        return _T()


def _args(path, **over):
    base = dict(reembed_ids=str(path), reembed_after_id=None, limit=100,
                batch=2, dry_run=False, reembed_verify=False)
    base.update(over)
    return SimpleNamespace(**base)


def _patch_embedder(monkeypatch, vec=None):
    import app.services.research_semantic as rs
    monkeypatch.setattr(rs, "embed_texts",
                        lambda texts: [vec or [1.0, 0.0] for _ in texts])
    monkeypatch.setattr(rs, "is_junk_headline", lambda h: "JUNK" in h)


def test_refresh_upserts_the_recomputed_vector_and_advances_the_cursor(tmp_path, monkeypatch):
    _patch_embedder(monkeypatch)
    p = tmp_path / "ids.txt"
    p.write_text("1\n2\n")
    conn = _FakeConn([{"id": 1, "headline": "hurac&#xE1;n hits the coast"},
                      {"id": 2, "headline": "second real headline here"}])

    assert asyncio.run(_reembed(conn, _args(p))) == 0

    upserts = [sql for sql, _ in conn.executed if "DO UPDATE" in sql]
    assert len(upserts) == 1
    ids_written = [a for sql, a in conn.executed if "DO UPDATE" in sql][0][0]
    assert ids_written == [1, 2]
    assert _load_reembed_cursor(p) == 2


def test_refresh_embeds_the_unescaped_headline_like_the_default_path(tmp_path, monkeypatch):
    seen = []
    import app.services.research_semantic as rs
    monkeypatch.setattr(rs, "embed_texts",
                        lambda texts: seen.extend(texts) or [[1.0, 0.0] for _ in texts])
    monkeypatch.setattr(rs, "is_junk_headline", lambda h: False)
    p = tmp_path / "ids.txt"
    p.write_text("1\n")
    conn = _FakeConn([{"id": 1, "headline": "cocaine worth &#xA3;1,000"}])

    asyncio.run(_reembed(conn, _args(p)))

    # entity decoded before embedding — a raw '&#xA3;' vector would be the bug
    assert seen == ["passage: cocaine worth £1,000"]


def test_dry_run_writes_nothing_and_leaves_the_cursor_alone(tmp_path, monkeypatch):
    _patch_embedder(monkeypatch)
    p = tmp_path / "ids.txt"
    p.write_text("1\n")
    conn = _FakeConn([{"id": 1, "headline": "a real headline goes here"}])

    asyncio.run(_reembed(conn, _args(p, dry_run=True)))

    assert not [sql for sql, _ in conn.executed if "DO UPDATE" in sql]
    assert _load_reembed_cursor(p) == 0


def test_junk_and_absent_ids_are_skipped_not_written(tmp_path, monkeypatch):
    _patch_embedder(monkeypatch)
    p = tmp_path / "ids.txt"
    p.write_text("1\n2\n3\n")  # 3 no longer exists in signals_v2
    conn = _FakeConn([{"id": 1, "headline": "JUNK Doc *.Shtml"},
                      {"id": 2, "headline": "a real headline goes here"}])

    asyncio.run(_reembed(conn, _args(p)))

    written = [a for sql, a in conn.executed if "DO UPDATE" in sql][0][0]
    assert written == [2]


def test_verify_reports_drift_against_the_stored_vector(tmp_path, monkeypatch, capsys):
    _patch_embedder(monkeypatch, vec=[1.0, 0.0])
    p = tmp_path / "ids.txt"
    p.write_text("1\n")
    # stored vector is orthogonal to what we now compute => cos 0.0
    conn = _FakeConn([{"id": 1, "headline": "a real headline goes here",
                       "vec": "[0.0,1.0]"}])

    asyncio.run(_reembed(conn, _args(p, reembed_verify=True)))

    err = capsys.readouterr().err
    assert "compared 1 stored vectors" in err
    assert "1 materially changed" in err


def test_cosine_is_the_plain_definition():
    assert _cosine([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
    assert _cosine([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)
    assert _cosine([0.0, 0.0], [1.0, 0.0]) == 0.0
