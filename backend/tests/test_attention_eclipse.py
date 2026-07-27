"""Attention-eclipse / under-the-radar pure logic.

The signal reads the SAME shared story-state as the rest of Atlas:
  - CONSEQUENCE = daily_edition.global_breadth_signal (language x country breadth)
  - MOVEMENT   = topic_movement velocity / surprise
and adds the one RELATIVE reading nothing else computes: attention SHARE (a
story's slice of the window's total coverage). Eclipse = high consequence + low
attention share, gated on the window being concentrated on a dominant event.
These are pure functions so the detector, gates, and ranking are unit-tested.
"""
import pytest

from app.services.attention_eclipse import (
    attention_concentration,
    consequence_score,
    lane_of,
    select_under_radar,
    EclipseCandidate,
)


# ── (a) eclipse detector — window-level concentration ────────────────────────

def test_concentration_diffuse_is_not_eclipse():
    # A spread-out day: no single story dominates -> no eclipse, stay quiet.
    # (Mirrors the live probe: real-now top1 ~4.5%, well under the 20% gate.)
    volumes = [100, 95, 90, 90, 85, 80, 80, 80, 75, 75]
    c = attention_concentration(volumes, eclipse_top1=0.20)
    assert c["eclipse"] is False
    assert c["top1_share"] < 0.20
    assert c["total"] == sum(volumes)


def test_concentration_dominant_event_is_eclipse():
    # One story holds ~45% of coverage (the World-Cup-final case).
    volumes = [900, 200, 200, 150, 150]  # 900 / 1600 = 0.5625
    c = attention_concentration(volumes, eclipse_top1=0.20)
    assert c["eclipse"] is True
    assert c["top1_share"] == pytest.approx(0.5625, abs=1e-3)
    assert c["dominant_index"] == 0
    assert c["hhi"] > 0.20


def test_concentration_empty_window_is_safe():
    c = attention_concentration([], eclipse_top1=0.20)
    assert c["eclipse"] is False
    assert c["total"] == 0
    assert c["top1_share"] == 0.0
    assert c["dominant_index"] is None


def test_concentration_dominant_index_is_argmax():
    c = attention_concentration([10, 80, 20], eclipse_top1=0.20)
    assert c["dominant_index"] == 1


# ── (c) consequence proxy — reuses global_breadth_signal + movement ──────────

def test_consequence_reuses_global_breadth():
    from app.services.daily_edition import global_breadth_signal
    # With no movement, consequence is driven purely by breadth (weight 0.6).
    breadth = global_breadth_signal(5, 6)  # = 1.0 (saturated)
    s = consequence_score(language_breadth=5, country_breadth=6, velocity=0.0, surprise=0.0)
    assert s == pytest.approx(0.6 * breadth, abs=1e-6)


def test_consequence_rewards_movement_and_surprise():
    quiet = consequence_score(language_breadth=5, country_breadth=6, velocity=0.0, surprise=0.0)
    moving = consequence_score(language_breadth=5, country_breadth=6, velocity=1.0, surprise=0.0)
    surprising = consequence_score(language_breadth=5, country_breadth=6, velocity=0.0, surprise=1.0)
    assert moving > quiet
    assert surprising > quiet
    # velocity sign does not matter — a fast decay is movement too.
    assert consequence_score(language_breadth=5, country_breadth=6, velocity=-1.0) == moving


def test_consequence_is_bounded_unit():
    s = consequence_score(language_breadth=99, country_breadth=99, velocity=99, surprise=99)
    assert 0.0 <= s <= 1.0


def test_consequence_low_for_single_language_local_story():
    # A one-language, few-country item (the trivia the naive ratio surfaced) is low.
    s = consequence_score(language_breadth=1, country_breadth=4, velocity=0.2, surprise=0.0)
    assert s < 0.4


# ── lane typing — DeepSeek category, NOT the buggy keyword classifier ─────────

def test_lane_uses_deepseek_category():
    assert lane_of("sports", "Trump FIFA World Cup Scandal") == "sports"
    assert lane_of("entertainment", "New Little House remake") == "entertainment"


def test_lane_general_default_and_bug_regression():
    # REGRESSION: classify_stream_lane('armed-conflict-escalation') wrongly returns
    # 'sports'. lane_of must keep a hard-news category label as general.
    assert lane_of(None, "armed-conflict-escalation") == "general"
    assert lane_of("armed_conflict", "US Bombards Iran Over Ormuz Attack") == "general"


def test_lane_soft_label_fallback_when_no_category():
    # No category typed yet -> soft keyword hint on the label catches obvious sport.
    assert lane_of(None, "2026 FIFA World Cup Final live") == "sports"


# ── (b)+(d) under-radar selection — honest ledger, no silent filtering ────────

def _cand(topic_id, label, attention, langs, countries, **kw):
    return EclipseCandidate(
        topic_id=topic_id, label=label, attention=attention,
        language_breadth=langs, country_breadth=countries,
        velocity=kw.get("velocity", 0.0), surprise=kw.get("surprise", 0.0),
        category=kw.get("category"), crisis_relevant=kw.get("crisis_relevant"),
        mean_cohesion=kw.get("mean_cohesion", 0.9),
        is_junk=kw.get("is_junk", False), is_roundup=kw.get("is_roundup", False),
    )


def _mixed_field():
    # One dominant event + a genuinely consequential quiet story + noise classes.
    return [
        _cand("dominant", "World Cup Final", attention=9000, langs=20, countries=120, category="sports"),
        _cand("dynamic-topic-42", "EU launches $1bn Gaza aid initiative", attention=42, langs=4, countries=18, velocity=-0.2),
        _cand("dynamic-topic-99", "US Bombards Iran Over Ormuz Attack", attention=120, langs=3, countries=17, velocity=0.46),
        _cand("dynamic-topic-7", "Bull gores runner in the face", attention=5, langs=1, countries=4),  # trivia
        _cand("dynamic-topic-8", "Naslovne strane za sredu", attention=90, langs=8, countries=36, is_roundup=True),  # roundup
        _cand("dynamic-topic-9", "Lauren Bennett kimdir grab-bag", attention=20, langs=3, countries=9, mean_cohesion=0.30),  # incoherent
        _cand("dynamic-topic-10", "Trump FIFA World Cup Scandal", attention=673, langs=5, countries=56, category="sports"),  # sports
    ]


def test_no_eclipse_window_surfaces_nothing_but_ledger_complete():
    # Diffuse field -> eclipse off -> nothing surfaced, but every candidate is
    # accounted for (no silent suppression).
    sel = select_under_radar(_mixed_field(), eclipse_on=False)
    assert sel.selected_ids == []
    assert len(sel.ledger) == len(_mixed_field())
    assert all("no_eclipse_window" in row.reason_codes for row in sel.ledger)


def test_eclipse_surfaces_consequential_low_share_story():
    sel = select_under_radar(_mixed_field(), eclipse_on=True, min_langs=3, min_countries=8)
    # The EU aid + US-Iran stories are consequential and low-share -> surfaced.
    assert "dynamic-topic-42" in sel.selected_ids
    assert "dynamic-topic-99" in sel.selected_ids
    # The dominant event itself is NOT under the radar.
    assert "dominant" not in sel.selected_ids


def test_ordered_by_lowest_attention_share_first():
    sel = select_under_radar(_mixed_field(), eclipse_on=True)
    # Among surfaced, the smallest-share consequential story leads.
    assert sel.selected_ids[0] == "dynamic-topic-42"  # attention 42 < 120


def test_naive_ratio_trivia_is_excluded_by_consequence_floor():
    # 'Bull gores runner' has the smallest attention (the naive ratio would rank it
    # #1) but fails the multi-language/multi-country floor -> not surfaced.
    sel = select_under_radar(_mixed_field(), eclipse_on=True)
    assert "dynamic-topic-7" not in sel.selected_ids
    row = next(r for r in sel.ledger if r.topic_id == "dynamic-topic-7")
    assert "below_consequence_floor" in row.reason_codes


def test_quality_classes_labeled_out_not_dropped():
    sel = select_under_radar(_mixed_field(), eclipse_on=True)
    by_id = {r.topic_id: r for r in sel.ledger}
    # roundup, grab-bag, and sports are all present in the ledger with a reason,
    # and none are selected (no silent filtering).
    assert "dynamic-topic-8" not in sel.selected_ids
    assert "roundup" in " ".join(by_id["dynamic-topic-8"].reason_codes)
    assert "dynamic-topic-9" not in sel.selected_ids
    assert "low_cohesion" in " ".join(by_id["dynamic-topic-9"].reason_codes)
    assert "dynamic-topic-10" not in sel.selected_ids
    assert "labeled_lane" in " ".join(by_id["dynamic-topic-10"].reason_codes)
    # every candidate appears exactly once in the ledger
    assert len(sel.ledger) == len(_mixed_field())


def test_dominant_event_reported():
    sel = select_under_radar(_mixed_field(), eclipse_on=True)
    assert sel.dominant["topic_id"] == "dominant"
    assert sel.dominant["attention"] == 9000


# ── wiring: DB rows -> concentration -> eclipse-gated selection ───────────────

def _row(topic_id, label, attention, langs, countries, **kw):
    return {"topic_id": topic_id, "label": label, "attention": attention,
            "langs": langs, "countries": countries,
            "velocity": kw.get("velocity", 0.0), "surprise": kw.get("surprise", 0.0),
            "category": kw.get("category"), "crisis_relevant": kw.get("crisis_relevant"),
            "mean_cohesion": kw.get("mean_cohesion", 0.9),
            "is_junk": kw.get("is_junk", False), "is_roundup": kw.get("is_roundup", False)}


def test_assemble_detects_eclipse_and_surfaces_from_rows():
    from app.services.attention_eclipse import assemble_eclipse
    rows = [
        _row("dominant", "World Cup Final", 9000, 20, 120, category="sports"),
        _row("dynamic-topic-42", "EU $1bn Gaza aid", 42, 4, 18),
        _row("dynamic-topic-99", "US Bombards Iran", 120, 3, 17, velocity=0.46),
    ]
    # NOTE (tier system, added by T5): sel.eclipse now means tier=='total' — both
    # the country_dominance/entropy_collapse axes lit AND the black-hole/thin-field
    # guards pass — not the raw top1-share gate alone (still exposed as
    # window['top1_share']/['hhi']). This fixture only has 3 rows, so field_size
    # is overridden to simulate a healthy field (guards would otherwise reject it
    # as thin, same as production would for a too-small candidate set) and the two
    # axes are supplied directly since this pure test doesn't compute them from a
    # real country-lead/entropy-baseline query. Preserves the original intent:
    # confirm an eclipsed window surfaces the consequential low-share stories.
    sel = assemble_eclipse(rows, eclipse_top1=0.20, country_dominance=0.5,
                           entropy_collapse=0.5, field_size=200)
    assert sel.tier == "total"
    assert sel.eclipse is True
    assert sel.window["top1_share"] > 0.20
    assert sel.window["hhi"] > 0.0
    assert "dynamic-topic-42" in sel.selected_ids


def test_assemble_stays_quiet_when_diffuse():
    from app.services.attention_eclipse import assemble_eclipse
    rows = [_row(f"t{i}", f"story {i}", vol, 4, 20)
            for i, vol in enumerate([100, 95, 90, 90, 85, 80, 80, 80, 75, 75])]
    sel = assemble_eclipse(rows, eclipse_top1=0.20)
    assert sel.eclipse is False
    assert sel.selected_ids == []
    assert len(sel.ledger) == len(rows)  # complete, nothing silently dropped


# ── field entropy + entropy collapse — coverage-diversity signals ────────────

from app.services.attention_eclipse import field_entropy, entropy_collapse

def test_field_entropy_uniform_is_high_and_concentrated_is_low():
    uniform = field_entropy([10, 10, 10, 10])
    concentrated = field_entropy([97, 1, 1, 1])
    assert uniform > concentrated
    assert field_entropy([]) == 0.0
    assert field_entropy([0, 0]) == 0.0

def test_entropy_collapse_ratio_and_nulls():
    assert entropy_collapse(0.5, 2.0) == 0.75
    assert entropy_collapse(0.5, None) is None
    assert entropy_collapse(0.5, 0.0) is None
    assert entropy_collapse(2.5, 2.0) == 0.0


from app.services.attention_eclipse import country_dominance

def test_country_dominance_fraction_and_zero_guard():
    assert country_dominance(30, 90) == 0.333333
    assert country_dominance(0, 0) == 0.0
    assert country_dominance(45, 45) == 1.0


from app.services.attention_eclipse import eclipse_guards

def _dom(**kw):
    base = dict(field_size=200, total_coverage=20000, dom_is_junk=False,
               dom_is_roundup=False, dom_cohesion=0.8, dom_langs=10, dom_countries=40)
    base.update(kw)
    return base

def test_eclipse_guards_pass_on_healthy_field():
    ok, reasons = eclipse_guards(**_dom())
    assert ok is True and reasons == []

def test_eclipse_guards_reject_thin_field_and_blackhole():
    ok, reasons = eclipse_guards(**_dom(field_size=31))
    assert ok is False and any("thin_field" in r for r in reasons)
    ok2, r2 = eclipse_guards(**_dom(dom_cohesion=0.2))
    assert ok2 is False and any("cohesion" in r for r in r2)
    ok3, r3 = eclipse_guards(**_dom(dom_countries=3))
    assert ok3 is False and "dominant_narrow_breadth" in r3


from app.services.attention_eclipse import classify_tier

def _axes(**kw):
    base = dict(guards_pass=True, guard_reasons=[], country_dominance=0.5,
               entropy_collapse=0.5, top1_share=0.3, hhi=0.2,
               dom_langs=10, dom_countries=40)
    base.update(kw)
    return base

def test_classify_tier_total_needs_both_axes():
    assert classify_tier(**_axes())["tier"] == "total"

def test_classify_tier_partial_on_one_axis():
    assert classify_tier(**_axes(entropy_collapse=0.0))["tier"] == "partial"
    assert classify_tier(**_axes(country_dominance=0.0))["tier"] == "partial"

def test_classify_tier_none_when_guards_fail_or_neither_axis():
    assert classify_tier(**_axes(guards_pass=False))["tier"] == "none"
    assert classify_tier(**_axes(country_dominance=0.0, entropy_collapse=0.0))["tier"] == "none"

def test_classify_tier_null_axes_do_not_crash():
    out = classify_tier(**_axes(entropy_collapse=None, country_dominance=0.5))
    assert out["tier"] == "partial"
    assert 0.0 <= out["intensity"] <= 1.0
    assert out["axes"]["entropy_collapse"] is None


# ── assemble_eclipse — tier/intensity/axes + dominant footprint ──────────────
# NOTE: named `_erow` (not `_row`) — a module already defines `_row` above with a
# different positional signature (topic_id, label, attention, langs, countries);
# redefining `_row` at module scope here would shadow it and break the two
# existing assemble_eclipse tests above that still call the old `_row`.

from app.services.attention_eclipse import assemble_eclipse

def _erow(topic_id, attention, **kw):
    base = dict(topic_id=topic_id, label=topic_id, attention=attention, langs=12,
                countries=40, velocity=0.0, surprise=0.0, category="armed-conflict",
                crisis_relevant=True, mean_cohesion=0.8, is_junk=False,
                is_roundup=False, identity_key=f"key-{topic_id}",
                country_codes=["US", "GB", "FR"])
    base.update(kw)
    return base

def test_assemble_eclipse_total_tier_with_axes_and_footprint():
    rows = [_erow("dominant", 5000)] + [_erow(f"s{i}", 20, countries=9, langs=4,
              country_codes=["BR", "AR"]) for i in range(60)]
    sel = assemble_eclipse(rows, country_dominance=0.5, entropy_collapse=0.5,
                           field_size=len(rows), total_coverage=sum(r["attention"] for r in rows))
    assert sel.tier == "total"
    assert sel.eclipse is True
    assert sel.dominant["identity_key"] == "key-dominant"
    assert sel.dominant["countries"] == ["US", "GB", "FR"]
    assert sel.axes["country_dominance"] == 0.5

def test_assemble_eclipse_guard_blocks_blackhole():
    rows = [_erow("blob", 5000, mean_cohesion=0.2)] + [_erow(f"s{i}", 20) for i in range(5)]
    sel = assemble_eclipse(rows, country_dominance=0.9, entropy_collapse=0.9,
                           field_size=len(rows), total_coverage=6000)
    assert sel.tier == "none"
    assert sel.eclipse is False
