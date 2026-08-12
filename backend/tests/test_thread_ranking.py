"""Unified narrative-thread ranking (Pedro, 2026-06-24).

The living/aggregate split was a source label dressed as quality: dynamic
clusters always ranked first, atlas topics filled below. But an atlas topic
that keeps growing is a live thread too — it shouldn't be demoted by origin.
rank_threads() scores ALL threads the same way, by movement + volume +
coherence, with no source bias:

- volume is log-damped so a 3,000-signal category can't bury a 50-signal story
  by raw count alone,
- movement (10h delta relative to size) lets a heating thread rise,
- coherence (avg_confidence) breaks ties toward real stories over loose bins.
"""
from __future__ import annotations

from app.services.thread_ranking import rank_threads


def _t(label, *, sc, ch, conf, source="dynamic"):
    return {"label": label, "signal_count": sc, "changed_10h": ch,
            "avg_confidence": conf, "source": source}


def test_empty():
    assert rank_threads([]) == []


def test_movement_breaks_a_volume_tie():
    hot = _t("hot", sc=100, ch=60, conf=0.5)
    cold = _t("cold", sc=100, ch=5, conf=0.5)
    assert [t["label"] for t in rank_threads([cold, hot])] == ["hot", "cold"]


def test_hot_small_story_can_outrank_stale_big_bin():
    # Pedro's case: a raw category must not dominate by volume alone.
    story = _t("US-Iran strikes", sc=50, ch=40, conf=0.9)
    bin_ = _t("Military Conflict", sc=3000, ch=20, conf=0.3)
    assert [t["label"] for t in rank_threads([bin_, story])][0] == "US-Iran strikes"


def test_confidence_breaks_a_near_tie():
    coherent = _t("coherent", sc=100, ch=20, conf=0.9)
    loose = _t("loose", sc=100, ch=20, conf=0.2)
    assert [t["label"] for t in rank_threads([loose, coherent])] == ["coherent", "loose"]


def test_source_field_does_not_bias_ranking():
    # identical metrics, different source → order must be stable, not source-led
    a = _t("a", sc=100, ch=20, conf=0.5, source="atlas")
    d = _t("d", sc=100, ch=20, conf=0.5, source="dynamic")
    ranked = [t["label"] for t in rank_threads([a, d])]
    assert set(ranked) == {"a", "d"}
    # swapping input order must not flip them (deterministic, source-agnostic)
    ranked2 = [t["label"] for t in rank_threads([d, a])]
    assert ranked == ranked2


def test_big_volume_still_helps_when_movement_and_coherence_equal():
    big = _t("big", sc=2000, ch=40, conf=0.5)
    small = _t("small", sc=40, ch=1, conf=0.5)
    # big has both more volume and more absolute movement → ranks first
    assert [t["label"] for t in rank_threads([small, big])][0] == "big"


def test_freak_movement_on_tiny_base_does_not_lead():
    # A 28-signal syndicated story whose changed_10h (53) exceeds its own
    # signal_count is noise/amplification — it must NOT out-rank a 766-signal
    # accelerating story for the front-page lead (movement is volume-damped).
    freak = _t("syndicated", sc=28, ch=53, conf=0.6)
    real = _t("real-mover", sc=766, ch=116, conf=0.6)
    assert [t["label"] for t in rank_threads([freak, real])][0] == "real-mover"


def test_lifestyle_thread_is_damped_below_a_comparable_real_thread():
    # 2026-06-29 §4(b): Vegas has the STRONGEST raw metrics - it would lead
    # without the damp (the live "Las Vegas Travel Guide ranks #1" pathology).
    # The editorial-lane damp drops it below real news, but it still appears
    # (input, not gate). Filler thread spreads the min-max normalisation.
    vegas = _t("Las Vegas Travel Guide", sc=300, ch=90, conf=0.97)
    iran = _t("Iran Attacks Bahrain and Kuwait", sc=250, ch=60, conf=0.90)
    filler = _t("Local council notes", sc=15, ch=1, conf=0.40)
    order = rank_threads([vegas, iran, filler])
    assert order[0]["label"] == "Iran Attacks Bahrain and Kuwait"
    labels = [t["label"] for t in order]
    assert "Las Vegas Travel Guide" in labels  # present, just no longer #1


def test_lane_damp_does_not_touch_real_news_ordering():
    from app.services.thread_ranking import lane_rank_multiplier
    assert lane_rank_multiplier({"label": "Iran Attacks Bahrain"}) == 1.0
    assert lane_rank_multiplier({"label": "Ukraine War Updates"}) == 1.0
    assert lane_rank_multiplier({"label": "World Cup 2026 Live Streams"}) < 1.0
    assert lane_rank_multiplier({"label": "Las Vegas Travel Guide"}) < 1.0


def _tb(label, *, sc, ch, conf, langs, countries):
    return {"label": label, "signal_count": sc, "changed_10h": ch,
            "avg_confidence": conf, "language_count": langs, "country_count": countries}


def test_global_breadth_lifts_a_multilingual_multicountry_story_over_a_local_volume_bin():
    # A genuinely global event (many languages + countries) outranks a bigger but
    # local, single-language thread — L2 now carries the L1 consequence signal.
    war = _tb("US-Iran war", sc=40, ch=10, conf=0.8, langs=5, countries=8)
    local = _tb("Local telco outage", sc=200, ch=8, conf=0.8, langs=1, countries=1)
    ranked = [t["label"] for t in rank_threads([local, war])]
    assert ranked[0] == "US-Iran war"


def test_thread_ranking_without_breadth_fields_still_ranks():
    a = {"label": "a", "signal_count": 100, "changed_10h": 20, "avg_confidence": 0.5}
    b = {"label": "b", "signal_count": 40, "changed_10h": 2, "avg_confidence": 0.5}
    ranked = [t["label"] for t in rank_threads([b, a])]
    assert ranked[0] == "a"


# ---------------------------------------------------------------------------
# RANK V2 (2026-07-18, Lane C): court damp + syndication damp + crisis nudge.
# All damps, never gates — every thread stays listed; env-reversible via
# ATLAS_RANK_V2=off (byte-identical old ranking).
# ---------------------------------------------------------------------------

def _evidence(pairs):
    """pairs = [(headline, source), ...] → evidence_samples shape."""
    return [{"headline": h, "source": s} for h, s in pairs]


def _syndicated_lifestyle():
    # Measured live case: fresh AU-syndication lifestyle burst — one wire piece
    # reprinted across one publisher family, near-identical headlines. Untyped
    # (category NULL, crisis_relevant None) so neither the category damp nor
    # the label-keyword lane catches it ("24K Gold Facial" has no lane token).
    return {
        "label": "24K Gold Facial", "signal_count": 77, "changed_10h": 45,
        "avg_confidence": 0.97, "language_count": 1, "country_count": 1,
        "crisis_relevant": None, "label_status": None,
        "evidence_samples": _evidence([
            ("The 24K gold facial taking over salons", "themercury.com.au"),
            ("The 24K gold facial taking over salons", "examiner.com.au"),
            ("The 24K gold facial taking over salons", "standard.net.au"),
            ("The 24K gold facial taking over salons", "themercury.com.au"),
            ("The 24K gold facial taking over salons", "examiner.com.au"),
            ("The 24K gold facial taking over salons", "borderMail.com.au"),
        ]),
    }


def _ukraine():
    # Multi-outlet, multi-language crisis story; court has not judged (NULL).
    return {
        "label": "Ukraine War Updates", "signal_count": 744, "changed_10h": 180,
        "avg_confidence": 0.85, "language_count": 6, "country_count": 12,
        "crisis_relevant": True, "label_status": None,
        "evidence_samples": _evidence([
            ("Russia strikes Kharkiv power grid", "bbc.com"),
            ("Ukraine claims advance near Bakhmut", "reuters.com"),
            ("Kyiv under drone attack overnight", "lemonde.fr"),
            ("Zelensky seeks new air defences", "dw.com"),
            ("Frappes russes sur Kharkiv", "france24.com"),
            ("Guerra en Ucrania: avance en el frente", "elpais.com"),
        ]),
    }


def _failed_blob():
    # Huge court-FAILED blob: label does not match its receipts. Diverse
    # sources (it absorbed everything), big volume — the old ranking loved it.
    return {
        "label": "Armed conflict escalation", "signal_count": 3770,
        "changed_10h": 220, "avg_confidence": 0.45,
        "language_count": 4, "country_count": 9,
        "crisis_relevant": True, "label_status": "failed",
        "evidence_samples": _evidence([
            ("Book review: a wartime memoir", "npr.org"),
            ("Local council votes on budget", "abc.net.au"),
            ("Film about conflict wins award", "variety.com"),
            ("Markets shrug off tensions", "ft.com"),
            ("Recipe: comfort food for hard times", "bonappetit.com"),
            ("Opinion: the rhetoric of escalation", "nytimes.com"),
        ]),
    }


def test_rank_v2_measured_live_case_ukraine_leads_blob_damped_lifestyle_listed(monkeypatch):
    monkeypatch.delenv("ATLAS_RANK_V2", raising=False)  # default = on
    lifestyle, ukraine, blob = _syndicated_lifestyle(), _ukraine(), _failed_blob()
    ranked = rank_threads([lifestyle, blob, ukraine])
    labels = [t["label"] for t in ranked]
    # The strong story leads.
    assert labels[0] == "Ukraine War Updates"
    # Court-failed blob is damped below the court-null real story.
    assert labels.index("Armed conflict escalation") > labels.index("Ukraine War Updates")
    # Lifestyle burst is LISTED (damp, never gate) — just not on top.
    assert "24K Gold Facial" in labels
    assert labels.index("24K Gold Facial") > labels.index("Ukraine War Updates")


def test_rank_v2_off_reverts_to_the_old_ranking(monkeypatch):
    # Minimal deterministic pair: identical metrics, one court-FAILED. The old
    # ranking ignores label_status entirely → both score identically and the
    # label tie-break (descending) puts "zzz-court-failed" first. v2 damps the
    # failed one below. The env var must flip between the two behaviours.
    failed = _t("zzz-court-failed", sc=100, ch=20, conf=0.8)
    failed["label_status"] = "failed"
    clean = _t("aaa-clean", sc=100, ch=20, conf=0.8)
    monkeypatch.setenv("ATLAS_RANK_V2", "off")
    old = [t["label"] for t in rank_threads([dict(failed), dict(clean)])]
    assert old == ["zzz-court-failed", "aaa-clean"]  # legacy: court invisible
    monkeypatch.delenv("ATLAS_RANK_V2", raising=False)  # default = on
    new = [t["label"] for t in rank_threads([dict(failed), dict(clean)])]
    assert new == ["aaa-clean", "zzz-court-failed"]  # v2: failed label sinks


def test_court_damp_failed_sinks_partial_dips_entailed_untouched(monkeypatch):
    monkeypatch.delenv("ATLAS_RANK_V2", raising=False)
    base = dict(sc=100, ch=20, conf=0.8)
    failed = _t("failed-label", **base)
    failed["label_status"] = "failed"
    partial = _t("partial-label", **base)
    partial["label_status"] = "partial"
    entailed = _t("entailed-label", **base)
    entailed["label_status"] = "entailed"
    nulled = _t("null-label", **base)
    ranked = [t["label"] for t in rank_threads([failed, partial, entailed, nulled])]
    # entailed/null (1.0) > partial (0.85) > failed (0.5)
    assert ranked.index("failed-label") == len(ranked) - 1
    assert ranked.index("partial-label") > ranked.index("entailed-label")
    assert ranked.index("partial-label") > ranked.index("null-label")


def test_syndication_damp_one_wire_reprint_loses_to_multi_outlet_coverage(monkeypatch):
    monkeypatch.delenv("ATLAS_RANK_V2", raising=False)
    # Same metrics; only the evidence differs: 6 reprints of one headline vs
    # 6 distinct outlet/headline pairs. Diversity damps the volume term only.
    reprint = _t("wire-reprint", sc=200, ch=20, conf=0.8)
    reprint["evidence_samples"] = _evidence(
        [("Same syndicated headline", f"paper{i}.com.au") for i in range(3)]
        + [("Same syndicated headline", "paper0.com.au")] * 3
    )
    organic = _t("organic-coverage", sc=180, ch=20, conf=0.8)
    organic["evidence_samples"] = _evidence(
        [(f"Distinct angle {i}", f"outlet{i}.com") for i in range(6)]
    )
    ranked = [t["label"] for t in rank_threads([reprint, organic])]
    assert ranked[0] == "organic-coverage"
    assert "wire-reprint" in ranked  # damped, never excluded


def test_headline_diversity_bounds_and_thin_evidence():
    from app.services.thread_ranking import headline_diversity
    # No evidence → cannot measure → no damp (honest 1.0).
    assert headline_diversity({}) == 1.0
    assert headline_diversity({"evidence_samples": []}) == 1.0
    # Thin evidence (<3 samples) → not enough to judge → 1.0.
    assert headline_diversity({"evidence_samples": _evidence(
        [("a", "x.com"), ("a", "y.com")])}) == 1.0
    # Fully identical wire copy clamps at the floor, never 0.
    flat = headline_diversity({"evidence_samples": _evidence(
        [("same", "one.com.au")] * 8)})
    assert flat == 0.4
    # Fully diverse coverage → 1.0.
    rich = headline_diversity({"evidence_samples": _evidence(
        [(f"h{i}", f"s{i}.com") for i in range(8)])})
    assert rich == 1.0


def test_headline_diversity_catches_the_measured_masthead_suffix_signature():
    # The LIVE 2026-07-18 case: one wire piece + " | <Masthead>" suffix across
    # 24 distinct .com.au domains (one publisher family). Distinct outlets AND
    # distinct raw headlines — only masthead-suffix stripping reveals the
    # reprint. Must clamp at the floor.
    from app.services.thread_ranking import headline_diversity
    mastheads = ["Katherine Times", "Blayney Chronicle", "The Scone Advocate",
                 "Namoi Valley Independent", "Dungog Chronicle", "Western Advocate"]
    samples = _evidence([
        (f"Automated assistant duped caller, raising ethical fears. | {m}",
         f"{m.lower().replace(' ', '')}.com.au")
        for m in mastheads
    ])
    assert headline_diversity({"evidence_samples": samples}) == 0.4


def test_crisis_lens_nudge_is_a_mild_tiebreak_not_a_gate(monkeypatch):
    monkeypatch.delenv("ATLAS_RANK_V2", raising=False)
    # Identical metrics: crisis_relevant=True wins the tie (+10%)...
    crisis = _t("crisis-story", sc=100, ch=20, conf=0.8)
    crisis["crisis_relevant"] = True
    farandula = _t("farandula-story", sc=100, ch=20, conf=0.8)
    farandula["crisis_relevant"] = False
    ranked = [t["label"] for t in rank_threads([farandula, crisis])]
    assert ranked[0] == "crisis-story"
    assert "farandula-story" in ranked  # stays listed — "you decide"
    # ...but a clearly stronger non-crisis story still beats a weak crisis one
    # (nudge is mild, never a gate).
    strong = _t("strong-noncrisis", sc=900, ch=200, conf=0.9)
    strong["crisis_relevant"] = False
    strong["language_count"], strong["country_count"] = 5, 10
    weak = _t("weak-crisis", sc=20, ch=1, conf=0.4)
    weak["crisis_relevant"] = True
    assert [t["label"] for t in rank_threads([weak, strong])][0] == "strong-noncrisis"


def test_correctly_typed_sport_is_damped_below_news_despite_global_breadth():
    # A World Cup match is genuinely multi-country/-language — the HIGHEST volume
    # and breadth here — but the semantic damp keeps it off the front page, so it
    # lands last behind the two real-news threads.
    football = {"label": "Suiza Elimina a Colombia", "signal_count": 60, "changed_10h": 20,
                "avg_confidence": 0.9, "language_count": 5, "country_count": 20,
                "crisis_relevant": False, "category": "Sports / World Cup"}
    war = {"label": "US-Iran war", "signal_count": 40, "changed_10h": 15,
           "avg_confidence": 0.8, "language_count": 2, "country_count": 6,
           "crisis_relevant": False, "category": "Armed conflict escalation"}
    election = {"label": "Election dispute", "signal_count": 30, "changed_10h": 10,
                "avg_confidence": 0.7, "language_count": 1, "country_count": 3,
                "crisis_relevant": False, "category": "Elections & Politics"}
    ranked = [t["label"] for t in rank_threads([football, war, election])]
    assert ranked[0] == "US-Iran war"  # real news leads, not the football
    # the sport is damped below the war despite carrying the highest breadth+volume
    assert ranked.index("Suiza Elimina a Colombia") > ranked.index("US-Iran war")


# ── T3.1 (i): the dash-masthead repair ──────────────────────────────────────
#
# M0 (docs/research/brief-daily/2026-08-12-m0-measurement.md §a.1/§a.7) measured
# the live witness `dynamic-topic-11877` ("Jalapeño Salmonella Outbreak"):
# 22 of its 26 raw 24h members are ONE wire piece stamped with a per-masthead
# EN-DASH suffix, yet the served `headline_diversity` was 1.000 — the maximum,
# no damp at all — because `_norm_headline` only stripped the PIPE stamp.
# These headlines are frozen verbatim from the M0 artifact's cluster dump.

JALAPENO_WIRE_FAMILY = [
    ("'Guac signal' sparked Chipotle's frantic bid to recall jalapeños "
     "– The Fort Morgan Times", "fortmorgantimes.com"),
    ("'Guac signal' sparked Chipotle's frantic bid to recall jalapeños "
     "– The Morning Call", "mcall.com"),
    ("'Guac signal' sparked Chipotle's frantic bid to recall jalapeños "
     "– Hazleton Standard Speaker", "standardspeaker.com"),
    ("'Guac signal' sparked Chipotle's frantic bid to recall jalapeños "
     "– The Press Democrat", "pressdemocrat.com"),
    ("'Guac signal' sparked Chipotle's frantic bid to recall jalapeños "
     "– Sun Sentinel", "sun-sentinel.com"),
    ("'Guac signal' sparked Chipotle's frantic bid to recall jalapeños "
     "– Orlando Sentinel", "orlandosentinel.com"),
    ("'Guac signal' sparked Chipotle's frantic bid to recall jalapeños "
     "– Wilkes-Barre Citizens' Voice", "citizensvoice.com"),
    ("'Guac signal' sparked Chipotle's frantic bid to recall jalapeños "
     "– San Diego Union-Tribune", "sandiegouniontribune.com"),
]


def test_norm_headline_folds_the_measured_en_dash_masthead_family():
    # The M0 witness: 8 distinct domains, 8 distinct raw headlines, ONE story.
    from app.services.thread_ranking import _norm_headline
    keys = {_norm_headline(h) for h, _ in JALAPENO_WIRE_FAMILY}
    assert len(keys) == 1, keys
    # and the surviving key is the STORY, not the masthead
    assert "jalapenos" in keys.pop()


def test_norm_headline_folds_em_dash_and_spaced_hyphen_stamps_too():
    from app.services.thread_ranking import _norm_headline
    story = ("Jalapeños linked to a US salmonella outbreak are tracked to a "
             "Mexican farm and a distributor")
    keys = {
        _norm_headline(f"{story} – Western Kansas News"),
        _norm_headline(f"{story} — Daily Camera"),
        _norm_headline(f"{story} - Lowell Sun"),
        _norm_headline(story),
    }
    assert len(keys) == 1, keys


def test_dash_strip_does_not_swallow_a_subtitle_or_a_short_headline():
    # The dash is prose punctuation, not a rare stamp like "|": the strip must
    # only fire when a LONG story side carries a SHORT stamp. Two genuinely
    # different stories that share a short dashed prefix stay distinct.
    from app.services.thread_ranking import _norm_headline
    assert _norm_headline("Ukraine war – live updates") != \
        _norm_headline("Ukraine war – Russia claims advance near Bakhmut")
    # a long story side with a LONG tail is a subtitle, not a masthead
    a = _norm_headline("Colombia quake death toll tops 250 as rescuers keep "
                       "searching – hopes fade for those still under rubble")
    b = _norm_headline("Colombia quake death toll tops 250 as rescuers keep "
                       "searching – survivors pulled out after three days")
    assert a != b


def test_headline_diversity_catches_the_measured_en_dash_signature():
    # The repair's consequence: the witness family now clamps at the floor
    # instead of scoring the maximum 1.000 it scored in production.
    from app.services.thread_ranking import headline_diversity
    assert headline_diversity({"evidence_samples": _evidence(
        JALAPENO_WIRE_FAMILY)}) == 0.4


def test_headline_diversity_denominator_counts_the_deduped_reprints():
    # M0 §a.2: the atlas evidence SQL is DISTINCT ON (LOWER(headline)), so one
    # wire piece running on 20 outlets arrives as ONE receipt carrying
    # syndication_count=20. Judging 4-of-4 distinct keys reads as full
    # diversity; the honest denominator is the raw signals those rows stand for.
    from app.services.thread_ranking import headline_diversity
    samples = [
        {"headline": "One wire piece everywhere", "source": "a.com",
         "syndication_count": 20},
        {"headline": "Second angle", "source": "b.com", "syndication_count": 1},
        {"headline": "Third angle", "source": "c.com", "syndication_count": 1},
        {"headline": "Fourth angle", "source": "d.com", "syndication_count": 1},
    ]
    assert headline_diversity({"evidence_samples": samples}) == 0.4
    # ...and a genuinely diverse thread with no reprints is untouched (the
    # dynamic lane serves syndication_count=1, so this path is byte-identical).
    plain = [{"headline": f"Angle {i}", "source": f"s{i}.com",
              "syndication_count": 1} for i in range(6)]
    assert headline_diversity({"evidence_samples": plain}) == 1.0
