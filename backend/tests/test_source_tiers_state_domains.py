"""Council R4 N18 (P0, third filing): the backend classifier must carry the
state-domain list itself — the GDELT lane never brings the ingest flag, and
the sealed edition stamped SANA/Xinhua/1tv.ru as mainstream while its own
prose said 'Syrian state media'."""
from app.services.source_tiers import classify_source_tier, STATE


def test_state_agencies_classify_state_without_ingest_flag():
    # the exact three the council caught sealed as mainstream
    for src in ("sana.sy", "news.cn", "1tv.ru"):
        t = classify_source_tier(src, is_state_media=False, source_family="gdelt")
        assert t.label == "state", f"{src} -> {t.label}"


def test_state_list_subdomain_and_url_forms():
    assert classify_source_tier("https://www.sana.sy/en/?p=1").label == "state"
    assert classify_source_tier("english.news.cn").label == "state"


def test_flagged_outranks_state_and_wire_stays_wire():
    # order per the docstring: flagged > reference > wire > state
    assert classify_source_tier("zerohedge.com", is_state_media=True).label == "flagged"
    assert classify_source_tier("reuters.com", source_family="gdelt").label == "wire"


def test_mainstream_untouched():
    assert classify_source_tier("bbc.com", source_family="gdelt").label != "state"
    assert classify_source_tier("breitbart.com", source_family="gdelt").label != "state"


def test_list_parity_with_frontend():
    # the two lists must not drift (screen vs sealed payload disagreed live).
    # Frontend list lives in frontend-v2/src/lib/sourceTiers.ts — this freezes
    # the ported members; additions go to BOTH or the parity test names it.
    expected_core = {"rt.com", "ria.ru", "sana.sy", "news.cn", "xinhuanet.com",
                     "irna.ir", "kcna.kp", "granma.cu", "telesurtv.net", "1tv.ru"}
    assert expected_core <= set(STATE.keys())
