"""Label ↔ receipt geography conjunct (council R4 N17).

The shared detector both guards ride: the court's geography conjunct
(scripts/label_court.py) and the country-edition slot guard
(app/services/country_edition.py). Every fixture here is a real witness or a
real near-miss pulled from production on 2026-08-11 — the N17 capstone
(dt-8597 'Japan Earthquake Traps Shoppers' over Colombia-quake receipts), its
sibling dt-3963, the Syros≈Syria case, and the two classes that must NOT fire.
"""
from app.services.subject_geography import (
    LABEL_GEO_DOMINANCE_FLOOR,
    LABEL_GEO_MIN_RECEIPTS,
    label_geography_conflict,
    label_subject_country,
    receipt_subject_country_counts,
)


def _r(*headlines: str) -> list[dict]:
    return [{"headline": h} for h in headlines]


# ── the N17 witness, frozen ───────────────────────────────────────────────────
# dt-8597, active, label_status='entailed' at the time of the council walk.
# 29 served receipts; the 19 that carry any subject geography ALL say Colombia,
# JP appears in none of them.
WITNESS_LABEL = "Japan Earthquake Traps Shoppers"
WITNESS_RECEIPTS = _r(
    "Terremoto de magnitud 7.4 sacudió gran parte de Colombia",
    "Potente sismo de 7,4 sacude a Colombia (VER IMÁGENES)",
    "Sismo de 7.4 sacude Colombia",
    "Colombia fue sacudida por un terremoto de magnitud 7,4: hay al menos 72 muertos",
    "Fuerte sismo de magnitud 7,4 sacude a gran parte Colombia",
)


def test_witness_label_names_exactly_one_country():
    assert label_subject_country(WITNESS_LABEL) == "JP"


def test_witness_conflict_fires_and_names_the_mismatch():
    conflict = label_geography_conflict(WITNESS_LABEL, WITNESS_RECEIPTS)
    assert conflict is not None
    assert conflict["label_country"] == "JP"
    assert conflict["dominant_country"] == "CO"
    assert conflict["dominant_receipts"] == 5
    assert conflict["geo_receipts"] == 5
    # the reason must NAME the mismatch, not just assert one
    assert conflict["summary"] == "label says Japan (JP); receipts 5/5 CO"


def test_sibling_witness_dt3963_also_fires():
    # 'Japan Earthquake Tsunami Alert' — same class, also stamped entailed
    conflict = label_geography_conflict(
        "Japan Earthquake Tsunami Alert",
        _r(
            "Colombia fue sacudida por un terremoto de magnitud 7,4: hay al menos 72 muertos",
            "Colombia fue sacudida por un terremoto de magnitud 7,5: hay al menos 18 muertos",
            "Terremoto 7,4 en Colombia: reportan al menos 22 muertos y edificios colapsados",
        ),
    )
    assert conflict is not None
    assert (conflict["label_country"], conflict["dominant_country"]) == ("JP", "CO")


# ── Syros ≈ Syria (the P-seat case) ──────────────────────────────────────────
# dt-4071 'Syros Rescuer Murder Suspect Remanded' serves on the SY edition
# because its signals are country-tagged SY. Neither the label ("Syros" is a
# Greek island absent from the shared lexicons AND from the GeoNames gazetteer
# — Ermoupoli is under the 15k city floor) nor the Greek receipts resolve to a
# country, so the conjunct ABSTAINS rather than guessing. Pinned deliberately:
# the honest limit of a detector that refuses to invent geography.
SYROS_RECEIPTS = _r(
    "Σύρος: Προσωρινά κρατούμενος στις φυλακές Χίου ο 41χρονος",
    "Σύρος: Προφυλακίστηκε ο δράστης της ανθρωποκτονίας της διασώστριας",
    "Σύρος: Ενώπιον του Συμβουλίου Πλημμελειοδικών σήμερα ο 41χρονος",
)


def test_syros_label_resolves_to_no_country_so_the_check_abstains():
    assert label_subject_country("Syros Rescuer Murder Suspect Remanded") is None
    assert label_geography_conflict(
        "Syros Rescuer Murder Suspect Remanded", SYROS_RECEIPTS) is None


def test_syros_class_fires_once_the_label_names_the_island_s_country():
    # the same story with a label that DOES make a geography claim ("Greek
    # island") over receipts dominated by another country is caught — the
    # class is covered wherever the geography is actually detectable.
    conflict = label_geography_conflict(
        "Greek Island Rescuer Murder Trial",
        _r(
            "Damascus court remands suspect over Syria paramedic killing",
            "Syria paramedic murder: suspect appears before Damascus judges",
            "Syrian rescuer killing — Damascus prosecutors seek detention",
        ),
    )
    assert conflict is not None
    assert (conflict["label_country"], conflict["dominant_country"]) == ("GR", "SY")


# ── negative cases: the check must abstain ───────────────────────────────────
def test_multi_country_label_skips_entirely():
    # a label naming two countries makes no single falsifiable claim
    assert label_subject_country("Russia Sanctions and Ukraine War Updates") is None
    assert label_geography_conflict(
        "Russia Sanctions and Ukraine War Updates",
        _r(
            "Russia strikes Kyiv as Ukraine presses for more air defence",
            "Germany approves new Ukraine aid package amid Russia sanctions push",
            "Moscow rejects Ukraine ceasefire terms; Berlin urges restraint",
        ),
    ) is None


def test_no_geo_label_skips_entirely():
    assert label_subject_country("Global Markets Rally on Rate Cut Hopes") is None
    assert label_geography_conflict(
        "Global Markets Rally on Rate Cut Hopes", WITNESS_RECEIPTS) is None


def test_person_proxy_label_is_not_a_geography_claim():
    # #238: a leader's name is candidate-grade subject geography at best, and
    # never a geography CLAIM the court may falsify.
    assert label_subject_country("Trump Tariffs Escalate") is None
    assert label_geography_conflict("Trump Tariffs Escalate", WITNESS_RECEIPTS) is None


def test_label_country_present_in_any_receipt_never_conflicts():
    conflict = label_geography_conflict(
        "Japan Earthquake Traps Shoppers",
        _r(
            "Terremoto de magnitud 7.4 sacudió gran parte de Colombia",
            "Sismo de 7.4 sacude Colombia",
            "Potente sismo de 7,4 sacude a Colombia",
            "Japan quake: shoppers trapped in collapsed mall",
        ),
    )
    assert conflict is None


def test_coverage_language_without_lexicon_geography_abstains():
    # dt-9434 'Japan Earthquake Casualties': ten Russian-tagged receipts that
    # are literally ABOUT Japan. The Cyrillic form of 'Japan' resolves to
    # nothing in the shared lexicons, so no geography is measured and the
    # check abstains — the class that would have produced a WRONG `failed`
    # had the conjunct compared against signals_v2.country_code (coverage).
    receipts = _r(
        "Число погибших при землетрясении в Японии выросло до 34",
        "Число жертв землетрясения в Японии выросло до 38 человек",
        "Понад 100 афтершоків сколихнули Японію після потужного землетрусу",
    )
    counts, carrying = receipt_subject_country_counts(receipts)
    assert (counts, carrying) == ({}, 0)
    assert label_geography_conflict("Japan Earthquake Casualties", receipts) is None


def test_too_few_geo_bearing_receipts_abstains():
    receipts = _r(
        "Sismo de 7.4 sacude Colombia",
        "Potente sismo de 7,4 sacude a Colombia",
        "Un temblor deja daños materiales en la region",
    )
    _, carrying = receipt_subject_country_counts(receipts)
    assert carrying == 2 < LABEL_GEO_MIN_RECEIPTS
    assert label_geography_conflict("Japan Earthquake Traps Shoppers", receipts) is None


def test_no_dominant_contradicting_country_abstains():
    # split field: no single other country holds the dominance floor
    receipts = _r(
        "Sismo sacude Colombia y deja daños",
        "Terremoto en Colombia: reportan heridos",
        "Sismo sacude Peru: hay evacuaciones en Lima",
        "Temblor en Chile obliga a evacuar Santiago",
        "Terremoto en Ecuador deja daños en Quito",
    )
    counts, carrying = receipt_subject_country_counts(receipts)
    assert carrying == 5 and counts["CO"] == 2
    assert counts["CO"] < LABEL_GEO_DOMINANCE_FLOOR * carrying
    assert label_geography_conflict("Japan Earthquake Traps Shoppers", receipts) is None


def test_empty_and_missing_inputs_are_safe():
    assert label_geography_conflict("", []) is None
    assert label_geography_conflict(None, None) is None
    assert label_geography_conflict("Japan Earthquake", [{}, {"headline": None}]) is None


def test_receipt_counts_are_per_receipt_not_per_mention():
    receipts = _r(
        "Colombia, Colombia, Colombia: sismo sacude Bogotá",
        "Sismo sacude Colombia",
        "Terremoto en Colombia deja heridos",
    )
    counts, carrying = receipt_subject_country_counts(receipts)
    assert counts == {"CO": 3}
    assert carrying == 3


# ── absence is checked wider than dominance (measured 2026-08-11) ─────────────
# On the judged 8-receipt window alone the check ran ~50% precise in a live
# 400-row sweep: every false positive was an ACTOR-vs-TARGET war label. The
# actor country IS named once the receipt window opens, so the wider absence
# pool separates "the label lies about its geography" from "the judged sample
# happened not to name the actor".
_ACTOR_LABEL = "Russian Drone Attacks on Emergency Workers"
_ACTOR_JUDGED = _r(
    "На Дніпропетровщині внаслідок атаки загинула дитина",
    "У Запоріжжі внаслідок повторного удару БпЛА загинув рятувальник",
    "Рятувальники в Україні гинуть під повторними ударами",
)


def test_actor_label_conflicts_on_the_narrow_window_alone():
    # the false positive the narrow check produced, reproduced exactly
    narrow = label_geography_conflict(_ACTOR_LABEL, _ACTOR_JUDGED)
    assert narrow is not None
    assert (narrow["label_country"], narrow["dominant_country"]) == ("RU", "UA")


def test_wider_absence_pool_clears_the_actor_label():
    wide = _ACTOR_JUDGED + _r(
        "Россия нанесла удар по Днепропетровщине",
        "Удар России по Запорожью: погиб спасатель",
    )
    assert label_geography_conflict(
        _ACTOR_LABEL, _ACTOR_JUDGED, absence_receipts=wide) is None


def test_wider_absence_pool_keeps_the_n17_witness_vetoed():
    # dt-8597 keeps JP at zero across 120 receipts — the widening never
    # rescues a label that genuinely names a country its story never mentions
    wide = WITNESS_RECEIPTS + _r(
        "Colombia: el sismo de 7,4 deja edificios colapsados en Manizales",
        "Terremoto en Colombia: continúan las labores de rescate",
        "Sismo en Colombia: reportan réplicas durante la madrugada",
    )
    conflict = label_geography_conflict(
        WITNESS_LABEL, WITNESS_RECEIPTS, absence_receipts=wide)
    assert conflict is not None
    assert conflict["dominant_receipts"] == 5   # dominance stays on the judged sample
    assert conflict["absence_pool"] == 8        # absence is measured wider
    assert conflict["absence_geo_receipts"] == 8


def test_absence_pool_defaults_to_the_judged_receipts():
    a = label_geography_conflict(WITNESS_LABEL, WITNESS_RECEIPTS)
    b = label_geography_conflict(WITNESS_LABEL, WITNESS_RECEIPTS,
                                 absence_receipts=WITNESS_RECEIPTS)
    assert a == b
