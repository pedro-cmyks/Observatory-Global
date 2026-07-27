"""HTML-entity-encoded headlines must never reach storage or dedup.

MEASURED (prod, 2026-07-22, 168h signals_v2): 432,873 / 932,719 press
headlines (46.4%) are stored entity-encoded — ``hurac&#xE1;n`` instead of
``huracán``. Concentration is one ingest lane: source_lang='xx' (the GDELT
TRANSLINGUAL feed) 79.4% encoded, 'en' (GDELT English) 6.6%, every declared
non-English RSS lane ~0.0%. Both encoded lanes come through the SAME writer,
``ingest_v2.parse_gkg_row`` (GKG V2EXTRASXML ``<PAGE_TITLE>``).

Two failures follow, both pinned here:

1. LEXICAL MATCHING dies silently. A folded token ``&#xE1;`` becomes ``xe1``,
   so the accented word simply does not exist in the corpus. Measured: the
   keyword 'huracan' scored 0 press matches against 16 real ones in the same
   48h window.
2. REPRINT DEDUP double-counts. 4,355 distinct headline texts appear in the
   corpus BOTH encoded and plain; a normalizer that does not unescape sees
   two different stories, inflating the volume that feeds the 0.45*log-volume
   term in rank_threads — i.e. distorting front-page thread order.

Prior art: the archive/embed writers already had to unescape before hashing
(``scripts/archive_embed_pipeline._norm``). That fix never reached ingest or
the serving-side normalizers.
"""
from __future__ import annotations

from pathlib import Path

import pytest

# "huracán" / "Çalhanoğlu" as GDELT stores them.
ENCODED = "Alerta por el hurac&#xE1;n Melissa"
PLAIN = "Alerta por el huracán Melissa"


class TestIngestWritesDecoded:
    def test_parse_gkg_row_decodes_page_title(self):
        from app.services.ingest_v2 import parse_gkg_row

        row = ["20260722120000", "", "", "outlet", "http://elpais.com/x"] + [""] * 22
        row[8] = "NATURAL_DISASTER"
        row[10] = "1#Mexico#MX##23.0#-102.0#00#20"
        row[26] = f"<PAGE_TITLE>{ENCODED}</PAGE_TITLE>"

        out = parse_gkg_row(row, source_lang="xx")

        assert out is not None
        assert out["headline"] == PLAIN
        assert "&#x" not in out["headline"]

    def test_non_latin_title_decoded_and_kept(self):
        """The translingual lane is where 79.4% of the encoding lives — a
        Turkish title must survive decoding, not get dropped by the >=4-word
        title validation."""
        from app.services.ingest_v2 import parse_gkg_row

        row = ["20260722120000", "", "", "outlet", "http://hurriyet.com.tr/x"] + [""] * 22
        row[10] = "1#Turkey#TU##39.0#35.0#00#20"
        row[26] = (
            "<PAGE_TITLE>Hakan &#xC7;alhano&#x11F;lu yeniden "
            "kadroya girdi</PAGE_TITLE>"
        )

        out = parse_gkg_row(row, source_lang="xx")

        assert out is not None
        assert out["headline"] == "Hakan Çalhanoğlu yeniden kadroya girdi"


class TestThreadRankingDedup:
    def test_norm_headline_folds_encoded_and_plain_together(self):
        from app.services.thread_ranking import _norm_headline

        assert _norm_headline(ENCODED) == _norm_headline(PLAIN)

    def test_encoded_and_plain_reprints_count_as_one_story(self):
        """The stored-corpus half of the bug: 4,355 headlines exist in both
        forms. Three receipts that are really ONE wire story must hit the
        diversity floor. Pre-fix the encoded copies read as separate stories
        and scored 2/3 = 0.667 — inflated volume feeding rank_threads."""
        from app.services.thread_ranking import headline_diversity

        samples = [
            {"source": f"outlet{i}.com", "headline": h}
            for i, h in enumerate([ENCODED, PLAIN, ENCODED])
        ]
        # 3 distinct outlets but 1 real headline -> headline_ratio binds,
        # clamped to the 0.4 floor.
        assert headline_diversity({"evidence_samples": samples}) == pytest.approx(0.4)


class TestDiacriticFolding:
    """Decoding is only half the recall fix.

    Once ``hurac&#xE1;n`` becomes ``huracán`` the word EXISTS, but a query for
    ``huracan`` still misses it, and two outlets writing the same story with
    and without accents still read as two stories. Search already closed its
    half (``f_unaccent`` both sides — the Mbappé hole, routers/search.py), so
    these normalizers are what is left.

    thread_ranking._norm_headline was worse than accent-sensitive: its
    ``[^a-z0-9]+`` class does not match ``á`` at all, so ``huracán`` folded to
    ``hurac n`` — the accented word shattered into fragments, exactly the
    failure the entity encoding caused.
    """

    ACCENTED = "Alerta por el huracán en Perú"
    UNACCENTED = "Alerta por el huracan en Peru"

    def test_norm_headline_folds_accents_instead_of_shattering_them(self):
        from app.services.thread_ranking import _norm_headline

        assert _norm_headline(self.ACCENTED) == _norm_headline(self.UNACCENTED)
        # and the word survives whole, rather than becoming "hurac n"
        assert "huracan" in _norm_headline(self.ACCENTED).split()

    def test_accent_variant_reprints_count_as_one_story(self):
        from app.services.thread_ranking import headline_diversity

        samples = [
            {"source": f"outlet{i}.com", "headline": h}
            for i, h in enumerate([self.ACCENTED, self.UNACCENTED, self.ACCENTED])
        ]
        assert headline_diversity({"evidence_samples": samples}) == pytest.approx(0.4)

    def test_gap_receipts_dedupe_across_accents_but_display_keeps_them(self):
        from app.services.gap_receipts import pick_extended_receipts

        rows = [
            {"headline": self.ACCENTED, "gate_score": 0.9, "source": "a", "url": "u1"},
            {"headline": self.UNACCENTED, "gate_score": 0.8, "source": "b", "url": "u2"},
        ]
        out = pick_extended_receipts(rows, threshold=0.5)

        assert len(out) == 1
        # folding is a KEY concern, never a display one — the reader gets the
        # headline as published.
        assert out[0]["headline"] == self.ACCENTED

    def test_thread_packet_person_corroboration_folds_accents(self):
        from datetime import datetime, timezone

        from app.services.thread_packet import build_thread_packet

        def _row(headline, person, outlet):
            return {"id": 1, "source_lang": "es",
                    "timestamp": datetime(2026, 7, 22, 10, tzinfo=timezone.utc),
                    "country_code": "PE", "source_name": outlet,
                    "source_url": f"http://{outlet}/x", "sentiment": -1.0,
                    "headline": headline, "themes": ["NATURAL_DISASTER"],
                    "persons": [person]}

        packet = build_thread_packet([
            _row("Boluarte declara emergencia", "dina boluarte", "a.pe"),
            _row("Boluarte viaja a la zona", "dina boluarte", "b.pe"),
            _row(self.ACCENTED, "cesar acuna", "c.pe"),
            _row(self.UNACCENTED, "cesar acuna", "d.pe"),
        ])

        names = {p["name"].lower() for p in packet["topPersons"]}
        assert "dina boluarte" in names
        assert "cesar acuna" not in names

    def test_query_thread_sql_folds_headline_accents(self):
        """The query-thread builder (/search/thread) still had the Mbappé hole
        that unified search closed: its LIKE patterns come from
        normalize_search_text (already accent-folded), so '%eleccion%' was
        compared against a raw 'elección' headline and never matched.

        Source-text assertion because the behaviour only shows against the
        production-sized table — same rationale as
        test_search_performance_shape. MEASURED on prod (24h): peru +16,
        eleccion +15, mexico +14, bogota +2 rows recovered. The folded form is
        also marginally FASTER (1.5s vs 1.8s) because f_unaccent(lower(
        headline)) is exactly the expression migration 064 indexed.
        """
        source = (Path(__file__).resolve().parents[1] / "app" / "routers"
                  / "search.py").read_text(encoding="utf-8")

        assert "LOWER(headline) LIKE ANY" not in source, (
            "every headline LIKE must fold accents on BOTH sides"
        )
        assert source.count("f_unaccent(LOWER(headline)) LIKE ANY") >= 2

    def test_query_thread_array_branches_use_indexed_expressions(self):
        """No OR-branch may be an unindexable expression.

        MEASURED 2026-07-22 (prod, 48h, one branch at a time): headline 0.3s
        and source_name 0.3s (both index-backed), while
        lower(array_to_string(themes|persons, ' ')) LIKE each ran past 45s and
        was cancelled. One rare keyword therefore blew the endpoint's 8s
        segment timeout. Migration 090 indexes both through the IMMUTABLE
        f_arr_text() wrapper (array_to_string is only STABLE), so the SQL must
        spell the branches EXACTLY as the indexes were built or the planner
        silently falls back to the seq scan this fixes.
        """
        source = (Path(__file__).resolve().parents[1] / "app" / "routers"
                  / "search.py").read_text(encoding="utf-8")

        assert "array_to_string(themes" not in source
        assert "array_to_string(persons" not in source
        assert "lower(f_arr_text(themes)) LIKE ANY" in source
        assert "f_unaccent(lower(f_arr_text(persons))) LIKE ANY" in source

    def test_syndication_audit_norm_folds_accents(self):
        import importlib.util

        path = (Path(__file__).resolve().parents[1] / "scripts"
                / "syndication_audit.py")
        spec = importlib.util.spec_from_file_location("syndication_audit", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        assert mod._norm(self.ACCENTED) == mod._norm(self.UNACCENTED)


class TestOtherHeadlineConsumers:
    def test_gap_receipts_dedupe_across_encodings(self):
        from app.services.gap_receipts import pick_extended_receipts

        rows = [
            {"headline": ENCODED, "gate_score": 0.9, "source": "a", "url": "u1"},
            {"headline": PLAIN, "gate_score": 0.8, "source": "b", "url": "u2"},
        ]
        out = pick_extended_receipts(rows, threshold=0.5)

        assert len(out) == 1
        assert out[0]["headline"] == PLAIN

    def test_thread_packet_person_corroboration_folds_encodings(self):
        """rank_key_people's corroboration floor (>=2 DISTINCT headlines) is
        the same syndication guard as headline_diversity. A person carried by
        ONE story stored twice — once encoded, once plain — must not clear the
        floor, or an encoding artifact fabricates corroboration."""
        from datetime import datetime, timezone

        from app.services.thread_packet import build_thread_packet

        def _row(headline, person, outlet):
            return {"id": 1, "source_lang": "es",
                    "timestamp": datetime(2026, 7, 22, 10, tzinfo=timezone.utc),
                    "country_code": "MX", "source_name": outlet,
                    "source_url": f"http://{outlet}/x", "sentiment": -1.0,
                    "headline": headline, "themes": ["NATURAL_DISASTER"],
                    "persons": [person]}

        packet = build_thread_packet([
            # genuinely corroborated: two different stories
            _row("Sheinbaum declara emergencia nacional", "claudia sheinbaum", "a.mx"),
            _row("Sheinbaum visita la zona afectada", "claudia sheinbaum", "b.mx"),
            # one wire story, stored in both encodings
            _row(ENCODED, "marcelo ebrard", "c.mx"),
            _row(PLAIN, "marcelo ebrard", "d.mx"),
        ])

        names = {p["name"].lower() for p in packet["topPersons"]}
        assert "claudia sheinbaum" in names
        assert "marcelo ebrard" not in names

    def test_backfill_cursor_roundtrips_and_survives_a_missing_file(self, tmp_path):
        """The nightly pass MUST persist its resume point. Measured
        2026-07-22: re-deriving it (scan from id 0 for the next still-encoded
        row) took >180s once ~196K rows were decoded and hit the pooler's
        statement_timeout, while the same query from the real cursor returned
        2,000 rows in 3.6s — the cost grows with progress, so a job that
        restarts at 0 gets slower until it can never finish."""
        import importlib.util

        path = (Path(__file__).resolve().parents[1] / "scripts"
                / "backfill_decode_headlines.py")
        spec = importlib.util.spec_from_file_location("backfill_decode", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        state = tmp_path / "cursor.json"
        assert mod._load_cursor(state) == 0          # first run
        mod._save_cursor(state, 13849802)
        assert mod._load_cursor(state) == 13849802   # resumes
        state.write_text("{ truncated", encoding="utf-8")
        assert mod._load_cursor(state) == 0          # torn file -> full pass

    def test_syndication_audit_norm_folds_encoded_and_plain(self):
        import importlib.util
        from pathlib import Path

        path = Path(__file__).resolve().parents[1] / "scripts" / "syndication_audit.py"
        spec = importlib.util.spec_from_file_location("syndication_audit", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        assert mod._norm(ENCODED) == mod._norm(PLAIN)
