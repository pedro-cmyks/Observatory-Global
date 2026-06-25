"""Contract: every per-signal serialization path in the /theme detail
response carries `id` and `source_lang`, so the frontend TranslatableHeadline
can translate non-English coverage articles (id = translation cache key,
source_lang = original language column on signals_v2).

Source-level checks rather than live DB: the bug class is a SELECT or a
serializer dict that silently omits the fields, which is a static property of
the code. Covers all four signals_v2-backed paths:
  - GDELT fallback (`signals` + `graphSignals` inline dicts),
  - atlas-topic `_sig` (+ its below-gate fallback, same serializer),
  - dynamic-topic + emergent-cluster (via build_thread_packet `_sig`).
"""
from __future__ import annotations

import re
from pathlib import Path

THEMES = (Path(__file__).resolve().parents[1] / "app" / "routers" /
          "themes.py").read_text(encoding="utf-8")
PACKET = (Path(__file__).resolve().parents[1] / "app" / "services" /
          "thread_packet.py").read_text(encoding="utf-8")


def test_gdelt_signal_queries_select_id_and_source_lang():
    # The two signals_v2 SELECTs feeding the GDELT-path `signals`/`graphSignals`
    # must both carry id + source_lang.
    assert THEMES.count("source_lang,\n                    timestamp") >= 2


def test_gdelt_serializers_emit_id_and_source_lang():
    # Both inline dict comprehensions (signals + graphSignals) emit the fields.
    assert THEMES.count('"id": r[\'id\'],') >= 2
    assert THEMES.count('"source_lang": r[\'source_lang\'],') >= 2


def test_atlas_topic_query_and_sig_carry_fields():
    # _atlas_topic_detail SELECT joins signals_v2 and must pull s.id + s.source_lang.
    assert "s.id, s.source_lang, s.timestamp" in THEMES
    # The _sig serializer (also used by the below-gate fallback) emits them.
    assert '"id": r["id"],' in THEMES
    assert '"source_lang": r["source_lang"],' in THEMES


def test_dynamic_and_emergent_queries_select_fields():
    # Both build_thread_packet-fed queries select s.id + s.source_lang.
    n = THEMES.count("SELECT s.id, s.source_lang, s.timestamp, s.country_code,"
                     " s.source_name,")
    assert n >= 2


def test_packet_serializer_emits_id_and_source_lang():
    # build_thread_packet._sig is the serializer for dynamic/emergent signals.
    assert '"id": _val(r, "id"),' in PACKET
    assert '"source_lang": _val(r, "source_lang"),' in PACKET
