"""Problema A — non-Latin geo-tagging (#150).

A headline written in a non-Latin script (Arabic, Persian, Urdu, Bengali,
Cyrillic, CJK, Devanagari) or in Turkish (Latin but distinct spellings) used
to match none of the English ``_COUNTRY_PATTERNS``, so ``extract_country``
returned ``None`` and the caller fell back to the *outlet's* home country —
mis-geotagging the story's subject (a DW-Arabic story about Syria tagged DE,
not SY).

These tests pin the SUBJECT lexicon end to end at the parse layer:

* Recall  — every target-language headline that names a country in native
            script tags that country (the Problema-A fix).
* Precision — country tokens that are substrings of unrelated words
            (مصر in مصرف "bank", عراق in عراقيل "obstacles", قطر in قطرة
            "drop") never produce a false tag.
* Fallback — a headline that names no country returns ``None`` so the caller
            can fall back to the outlet country (the contract callers rely on).
* Regression — the existing Latin and CJK/Cyrillic paths still work.

The two aggregate tests encode the bar: recall AND precision must be 100% —
not merely "passes", but excellent.
"""
from __future__ import annotations

import pytest

from app.services.ingest_rss import extract_country
from app.services.subject_geography import (
    infer_receipt_subject_geography,
    measure_subject_geography_coherence,
    resolve_place_to_country,
)


# ── Recall: (label, headline, expected ISO2) ──────────────────────────────────
# Headlines are realistic phrasings a real outlet would publish, each naming
# its subject country in native script.
RECALL_CASES: list[tuple[str, str, str]] = [
    # ── Arabic (ar) — pan-Arab + MENA + majors ──
    ("ar Egypt", "الانتخابات في مصر تشهد إقبالا واسعا", "EG"),
    ("ar Saudi", "السعودية تعلن عن استثمارات جديدة", "SA"),
    ("ar Iraq", "العراق يستعد للانتخابات البرلمانية", "IQ"),
    ("ar Lebanon", "تفاقم الأزمة الاقتصادية في لبنان", "LB"),
    ("ar Yemen", "الحوثيون في اليمن يستهدفون السفن", "YE"),
    ("ar Sudan", "تواصل الحرب في السودان لليوم المئة", "SD"),
    ("ar Libya", "اشتباكات جديدة في ليبيا", "LY"),
    ("ar Jordan", "الأردن يستضيف قمة إقليمية", "JO"),
    ("ar Syria", "قصف يستهدف العاصمة السورية دمشق", "SY"),
    ("ar Gaza", "الحرب في غزة تدخل شهرها العاشر", "GZ"),
    ("ar Qatar", "قطر تستضيف مفاوضات الوساطة", "QA"),
    ("ar UAE", "الإمارات تطلق مشروعا للطاقة", "AE"),
    ("ar Kuwait", "الكويت تعلن موازنة جديدة", "KW"),
    ("ar Morocco", "المغرب يفوز بتنظيم البطولة", "MA"),
    ("ar Tunisia", "انتخابات رئاسية في تونس", "TN"),
    ("ar Algeria", "الجزائر توقع اتفاقا للغاز", "DZ"),
    ("ar Turkey", "تركيا تتدخل في الملف السوري", "TR"),  # TR must win over SY
    ("ar Iran>Israel", "تصاعد التوتر بين إيران وإسرائيل", "IR"),  # priority
    ("ar Russia>Ukraine", "تتواصل الحرب بين روسيا وأوكرانيا", "RU"),  # priority
    ("ar China", "الصين تعلن نموا اقتصاديا", "CN"),
    ("ar Pakistan>Afghan", "توتر على الحدود بين باكستان وأفغانستان", "PK"),  # priority
    ("ar USA", "الولايات المتحدة تفرض عقوبات جديدة", "US"),
    ("ar Germany", "ألمانيا تستعد للانتخابات", "DE"),
    ("ar India", "الهند تطلق قمرا صناعيا", "IN"),

    # ── Turkish (tr) — Latin script, Turkish spellings ──
    ("tr Syria", "Suriye'de yeni çatışmalar başladı", "SY"),
    ("tr Iran", "İran ile gerilim tırmanıyor", "IR"),
    ("tr Greece", "Yunanistan'da erken seçim kararı", "GR"),
    ("tr Turkey", "Türkiye ekonomisinde toparlanma", "TR"),
    ("tr Russia>Ukraine", "Rusya ve Ukrayna arasında savaş sürüyor", "RU"),  # priority
    ("tr Egypt", "Mısır'da siyasi gelişmeler", "EG"),
    ("tr Iraq", "Irak sınırında askeri operasyon", "IQ"),
    ("tr USA", "ABD'den yeni yaptırımlar geldi", "US"),
    ("tr China", "Çin ekonomisi hızla büyüyor", "CN"),
    ("tr Palestine", "Filistin meselesi yeniden gündemde", "GZ"),
    ("tr Israel", "İsrail'in saldırıları sürüyor", "IL"),
    ("tr Germany", "Almanya'da koalisyon görüşmeleri", "DE"),

    # ── Urdu (ur) — Arabic script, Pakistani spellings ──
    ("ur Pakistan", "پاکستان میں سیاسی بحران شدت اختیار کر گیا", "PK"),
    ("ur India", "بھارت کے ساتھ کشیدگی میں اضافہ", "IN"),
    ("ur Afghanistan", "افغانستان کی صورتحال پر تشویش", "AF"),
    ("ur Iran", "ایران پر فضائی حملہ", "IR"),
    ("ur China", "چین کا بڑا اعلان", "CN"),
    ("ur USA", "امریکہ کی نئی پابندیاں", "US"),
    ("ur Israel", "اسرائیل کی جارحیت جاری", "IL"),
    ("ur Palestine", "فلسطین کاز کے لیے حمایت", "GZ"),
    ("ur Russia>Ukraine", "روس اور یوکرین کے درمیان جنگ", "RU"),  # priority
    ("ur Saudi", "سعودی عرب کا اہم دورہ", "SA"),

    # ── Bengali (bn) — Bengali script, Bangladeshi spellings ──
    ("bn Bangladesh", "বাংলাদেশে নির্বাচন নিয়ে উত্তেজনা", "BD"),
    ("bn India", "ভারতের সঙ্গে সীমান্ত উত্তেজনা", "IN"),
    ("bn Pakistan", "পাকিস্তানে বড় হামলা", "PK"),
    ("bn China", "চীনের অর্থনীতি নিয়ে উদ্বেগ", "CN"),
    ("bn USA", "যুক্তরাষ্ট্রের নতুন নিষেধাজ্ঞা", "US"),
    ("bn Russia>Ukraine", "রাশিয়া ও ইউক্রেনের মধ্যে যুদ্ধ", "RU"),  # priority
    ("bn Iran", "ইরানে বিক্ষোভ ছড়িয়ে পড়েছে", "IR"),
    ("bn Israel", "ইসরায়েলের হামলায় হতাহত", "IL"),
    ("bn Gaza", "গাজায় যুদ্ধ অব্যাহত", "GZ"),
    ("bn Myanmar", "মিয়ানমারে নতুন করে সহিংসতা", "MM"),

    # ── Persian (fa) — extend the existing lane ──
    ("fa Iran>USA", "تنش میان ایران و آمریکا بالا گرفت", "IR"),  # priority
    ("fa Syria", "ادامه جنگ در سوریه", "SY"),
    ("fa Afghanistan", "بحران در افغانستان عمیق‌تر شد", "AF"),
    ("fa Saudi", "عربستان سعودی توافق جدیدی امضا کرد", "SA"),
    ("fa Turkey", "ترکیه در مرز عملیات نظامی آغاز کرد", "TR"),
    ("fa Russia", "حمله روسیه به اوکراین ادامه دارد", "RU"),

    # ── Regression: existing CJK / Cyrillic / Devanagari ──
    ("zh China", "中国经济数据公布", "CN"),
    ("ja Japan", "日本の選挙結果速報", "JP"),
    ("ko Korea", "한국 뉴스 속보", "KR"),
    ("ru Russia>Ukraine", "Россия и Украина продолжают войну", "RU"),
    ("hi India", "भारत में चुनाव की तैयारी", "IN"),

    # ── Regression: Latin still works ──
    ("en Iran>USA", "Iran strikes US base in overnight raid", "IR"),
    ("es Colombia", "Elecciones presidenciales en Colombia", "CO"),

    # ── Demonyms (nisba adjectives) — Arabic/Persian press names the actor by
    # adjective far more than by country noun ("the Egyptian team", not "Egypt").
    # Single-subject headlines so the expected tag is deterministic.
    ("ar demonym Egypt", "المنتخب المصري يتأهل إلى النهائي", "EG"),
    ("ar demonym Sudan", "الوفد السوداني يصل إلى طاولة المفاوضات", "SD"),
    ("ar demonym Iraq", "الشعب العراقي يطالب بالإصلاح", "IQ"),
    ("ar demonym Lebanon", "الجيش اللبناني ينتشر في الجنوب", "LB"),
    ("ar demonym Saudi", "العاهل السعودي يفتتح القمة", "SA"),
    ("ar demonym Syria", "الرئيس السوري يلقي خطابا", "SY"),
    ("ar demonym Iran", "البرنامج النووي الإيراني تحت المراقبة", "IR"),
    ("ar demonym China", "الاقتصاد الصيني يواصل النمو", "CN"),
    ("ar demonym Pakistan", "الجيش الباكستاني يعلن عملية جديدة", "PK"),
    ("ar demonym India", "الوفد الهندي يشارك في القمة", "IN"),
    ("ar demonym Israel", "الجيش الإسرائيلي يواصل غاراته", "IL"),
    ("ar demonym Palestine", "الشعب الفلسطيني يطالب بوقف الحرب", "GZ"),
    ("fa demonym Iran", "برنامه هسته‌ای ایرانی در دستور کار", "IR"),
    ("fa demonym China", "اقتصاد چینی در حال رشد است", "CN"),
]


# ── Precision: (label, headline, forbidden ISO2, expected-result) ──────────────
# A country token that is a substring of an unrelated word must never fire.
# expected is the correct answer: None for pure traps, or the real country
# when a trap word co-occurs with a genuine country.
PRECISION_CASES: list[tuple[str, str, str, str | None]] = [
    # مصرف = "bank" contains مصر (Egypt). Real subject is Lebanon.
    ("ar bank not Egypt", "أزمة في مصرف لبنان المركزي", "EG", "LB"),
    # عراقيل = "obstacles" contains عراق (Iraq). No real country.
    ("ar obstacles not Iraq", "واجهت الخطة عراقيل كثيرة هذا العام", "IQ", None),
    # قطرة = "a drop" contains قطر (Qatar). No real country.
    ("ar drop not Qatar", "سقطت قطرة مطر على النافذة", "QA", None),
    # أيمن = the name "Ayman" contains يمن (Yemen). No real country.
    ("ar name not Yemen", "أيمن يعمل في شركة كبيرة", "YE", None),
    # بھروسا = "trust" (Urdu) contains روس (Russia). No real country.
    ("ur trust not Russia", "مجھے تم پر پورا بھروسا ہے", "RU", None),
    # Çince = "the Chinese language" contains Çin (China). It's the language,
    # not the country — must not tag CN.
    ("tr language not China", "Çince öğrenmeye başladım", "CN", None),
]


# ── Fallback: headlines that name NO country must return None ──────────────────
NONE_CASES: list[tuple[str, str]] = [
    ("ar neutral", "الاقتصاد العالمي في حال نمو مستمر"),
    ("fa neutral", "بازارهای جهانی امروز رشد کردند"),
    ("en neutral", "Global markets rally on strong tech earnings"),
    ("empty", ""),
]


@pytest.mark.parametrize("label,headline,expected", RECALL_CASES, ids=[c[0] for c in RECALL_CASES])
def test_recall_native_subject_tagging(label, headline, expected):
    assert extract_country(headline, "") == expected


@pytest.mark.parametrize(
    "label,headline,forbidden,expected",
    PRECISION_CASES,
    ids=[c[0] for c in PRECISION_CASES],
)
def test_precision_no_substring_false_positive(label, headline, forbidden, expected):
    result = extract_country(headline, "")
    assert result != forbidden, f"false positive {forbidden} on {label!r}"
    assert result == expected


@pytest.mark.parametrize("label,headline", NONE_CASES, ids=[c[0] for c in NONE_CASES])
def test_no_country_returns_none(label, headline):
    assert extract_country(headline, "") is None


def test_recall_is_perfect_over_gold_set():
    """Excellence bar: 100% recall over the gold subject set."""
    misses = [
        (label, headline, expected, extract_country(headline, ""))
        for label, headline, expected in RECALL_CASES
        if extract_country(headline, "") != expected
    ]
    rate = 1 - len(misses) / len(RECALL_CASES)
    assert not misses, f"recall {rate:.1%} — misses: {misses}"


def test_precision_is_perfect_over_adversarial_set():
    """Excellence bar: 100% precision — zero substring false positives."""
    fails = [
        (label, forbidden, extract_country(headline, ""))
        for label, headline, forbidden, expected in PRECISION_CASES
        if extract_country(headline, "") == forbidden
        or extract_country(headline, "") != expected
    ]
    assert not fails, f"precision failures: {fails}"


# ── Subject is the TITLE, never an incidental body mention ────────────────────
# Confirmed bug: an Australian opinion column ("Pauline Hanson will be her own
# downfall…", areanews.com.au, source_origin_country=AU) whose syndicated
# description carried a France token (France/French/Paris/Macron) was
# confidently tagged FR — surfacing "concentrated in France" + FRANCE chips on
# an Australian story. extract_country tags the SUBJECT from the title only; a
# passing country mention in the snippet/body must NOT assert that country.
# When the title names no country, extract_country returns None so the caller
# falls back to a reliable signal (outlet home country / provider country
# field), never a body mention.
#
# (label, title, snippet, expected)
TITLE_SUBJECT_CASES: list[tuple[str, str, str, str | None]] = [
    # The confirmed false positive, with realistic syndicated-body France tokens.
    (
        "AU column, France in body 'Paris'",
        "Adam Triggs | Pauline Hanson will be her own downfall if she keeps talking",
        "Opinion: The One Nation senator's repeated outbursts are eroding her base. "
        "More stories: Bastille Day crowds gather in Paris; local council budget passes.",
        None,
    ),
    (
        "AU column, France in body 'France'/'French'",
        "Pauline Hanson will be her own downfall if she keeps talking",
        "Related reading from across our network: France braces for strike; "
        "French unions reject pension reform. Subscribe to the Area News newsletter.",
        None,
    ),
    (
        "AU column, France in body 'Macron'",
        "Pauline Hanson will be her own downfall if she keeps talking",
        "In other news, Macron addressed parliament on the economy this week.",
        None,
    ),
    # Guardrail: a headline that GENUINELY names France must still resolve FR —
    # the fix kills the false positive without killing legitimate detection.
    (
        "real France headline still FR",
        "Macron calls snap election as France faces political crisis",
        "Paris — The president dissolved the National Assembly on Sunday.",
        "FR",
    ),
    (
        "France subject even with AU-irrelevant body",
        "France unveils new nuclear strategy in Paris",
        "Sydney markets opened higher on Monday.",  # incidental body mention ignored
        "FR",
    ),
    # A country named ONLY in the body does not tag the signal — caller falls
    # back. (Recovering real body subjects is the e5/NLP geo path, not keywords.)
    (
        "subject only in body → None (caller falls back)",
        "Breaking: latest developments and analysis",
        "Russia launched a fresh wave of strikes on Kyiv overnight, Ukraine said.",
        None,
    ),
]


@pytest.mark.parametrize(
    "label,title,snippet,expected",
    TITLE_SUBJECT_CASES,
    ids=[c[0] for c in TITLE_SUBJECT_CASES],
)
def test_subject_from_title_not_incidental_body(label, title, snippet, expected):
    assert extract_country(title, snippet) == expected, label


def test_pauline_hanson_not_france():
    """The exact reported false positive: AU column, FR token in the body."""
    title = "Adam Triggs | Pauline Hanson will be her own downfall if she keeps talking"
    snippet = (
        "The One Nation senator keeps talking herself into trouble. "
        "Elsewhere: Macron and France's parliament clash over the budget in Paris."
    )
    result = extract_country(title, snippet)
    assert result != "FR", f"regression: AU column mis-tagged FR (got {result!r})"
    assert result is None, (
        "title names no country → expected None so the caller falls back to the "
        f"outlet's AU home country, got {result!r}"
    )


# ── High-volume subject countries (2026-07-13 generalization pass) ────────────
# The publication generalization probe measured who/where readiness at ~50%
# because Australia, Belgium, Switzerland, Canada, the Netherlands, Poland,
# Spain, Italy, Japan, South Korea and the Nordics were absent from
# _COUNTRY_PATTERNS entirely, so their stories could never verify subject
# geography from a headline. These recall/precision cases pin the new lexicon.
_ADDED_RECALL = [
    ("belgium_fr", "Canicule attendue en Belgique cette semaine", "BE"),
    ("belgium_en", "Belgium heatwave breaks records across Brussels", "BE"),
    ("australia_city", "Man missing from Bondi Beach as Sydney police appeal", "AU"),
    ("australia_name", "Australian bowls star Jacky Hudson honoured", "AU"),
    ("switzerland_es", "Suiza gana y complica al grupo en el Mundial", "CH"),
    ("switzerland_en", "Zurich and Geneva brace as Switzerland debates rules", "CH"),
    ("canada", "Ottawa unveils new Canadian trade policy", "CA"),
    ("netherlands", "Dutch coalition debates Amsterdam housing crunch", "NL"),
    ("poland", "Warsaw summit gathers Poland's regional allies", "PL"),
    ("spain", "Barcelona rallies as Madrid debates the España budget", "ES"),
    ("italy", "Rome and Naples brace for an Italian rail strike", "IT"),
    ("japan", "Tokyo markets rattle as Japan revises its policy", "JP"),
    ("south_korea", "Seoul housing prices surge across South Korea", "KR"),
    ("portugal", "Lisbon protest grows as Portugal debates labour law", "PT"),
    ("ireland", "Dublin readies as Ireland reviews the budget", "IE"),
]

_ADDED_PRECISION = [
    # common words / demonyms deliberately excluded must not false-fire
    ("polish_verb", "How to polish your shoes at home", "PL", None),
    ("spanish_language", "The report was published in Spanish", "ES", None),
    ("austria_not_australia", "Vienna hosts an Austria climate summit", "AU", "AT"),
]


@pytest.mark.parametrize("label,headline,expected", _ADDED_RECALL, ids=[c[0] for c in _ADDED_RECALL])
def test_added_country_recall(label, headline, expected):
    assert extract_country(headline, "") == expected


@pytest.mark.parametrize(
    "label,headline,forbidden,expected", _ADDED_PRECISION, ids=[c[0] for c in _ADDED_PRECISION],
)
def test_added_country_precision(label, headline, forbidden, expected):
    result = extract_country(headline, "")
    assert result != forbidden, f"false positive {forbidden} on {label!r} (got {result!r})"
    assert result == expected


def test_added_countries_verify_subject_geography_from_receipts():
    """The subject-geography decoder now corroborates the added countries when
    two receipts from two outlets name one in the headline (the publishable bar)."""
    receipts = [
        {"id": 1, "headline": "Heatwave grips Belgium as Brussels issues alert", "source_name": "Reuters"},
        {"id": 2, "headline": "Belgium swelters, Belgique records broken", "source_name": "AFP"},
    ]
    result = infer_receipt_subject_geography(receipts)
    assert result["status"] == "verified"
    assert result["verified_subject_countries"] == ["BE"]


# ── Umbrella coherence (#257): co-occurrence separates one multi-country story
# from a grab-bag of unrelated country-stories bundled under one label ─────────
def test_coherence_multi_country_story_that_co_occurs_is_not_a_grab_bag():
    # One story genuinely spanning three countries: every receipt names them
    # together, so the countries co-occur.
    receipts = [
        {"headline": "Israel warns US of Iranian plot to assassinate Trump"},
        {"headline": "US and Israel brief allies on Iran assassination plot"},
        {"headline": "Iran denies Israel-US claims of a Trump plot"},
    ]
    result = measure_subject_geography_coherence(receipts)
    assert result["grab_bag"] is False
    assert result["status"] == "coherent_multi_country"
    assert set(result["significant_countries"]) >= {"IR", "IL", "US"}


def test_coherence_disjoint_country_groups_are_flagged_as_grab_bag():
    # Two unrelated stories bundled: Belgium heatwave receipts and France budget
    # receipts never co-occur — an incoherent umbrella (the #257 failure mode).
    receipts = [
        {"headline": "Heatwave grips Belgium as Brussels issues alert"},
        {"headline": "Belgium swelters as Brussels breaks records"},
        {"headline": "Belgique en canicule cette semaine"},
        {"headline": "France debates budget in Paris"},
        {"headline": "Paris braces as France reviews spending"},
        {"headline": "France budget vote looms in Paris"},
    ]
    result = measure_subject_geography_coherence(receipts)
    assert result["grab_bag"] is True
    assert result["status"] == "grab_bag"
    assert set(result["significant_countries"]) >= {"BE", "FR"}
    assert "disjoint_country_groups_grab_bag" in result["reason_codes"]


def test_coherence_single_subject_is_not_a_grab_bag():
    receipts = [
        {"headline": "Iran expands drought response as Tehran rations water"},
        {"headline": "Iran reservoirs fall to record lows"},
    ]
    result = measure_subject_geography_coherence(receipts)
    assert result["grab_bag"] is False
    assert result["status"] == "single_dominant_subject"


def test_coherence_abstains_without_geo_signal():
    receipts = [{"headline": "Local council debates parking rules"}]
    result = measure_subject_geography_coherence(receipts)
    assert result["grab_bag"] is False
    assert result["status"] == "no_subject_geography_signal"


# ── NER place → country (C-clean slice 1): resolve places named in the story
# body (via NER) to a subject country, for headlines that name only a local
# entity. The resolver reuses the shared country patterns (which include
# capitals/major cities); obscure places return None — the gazetteer ceiling. ──
@pytest.mark.parametrize("place,expected", [
    ("Sydney", "AU"),
    ("Melbourne", "AU"),
    ("Brussels", "BE"),
    ("Tehran", "IR"),
    ("Toronto", "CA"),
    ("Bondi Beach", None),   # not in the gazetteer — honest None, no guess
    ("", None),
])
def test_resolve_place_to_country(place, expected):
    assert resolve_place_to_country(place) == expected


def test_subject_geography_verifies_from_ner_places_when_headline_is_silent():
    # Oblique-headline local story: the headline names a company (Telstra), not a
    # country, but NER extracted the city from the body. Two receipts, two
    # outlets naming Australian cities → verified AU subject geography.
    receipts = [
        {"id": 1, "headline": "Telstra outage hits thousands", "source_name": "R", "places": ["Sydney"]},
        {"id": 2, "headline": "Telstra network slowly restored", "source_name": "A", "places": ["Melbourne"]},
    ]
    result = infer_receipt_subject_geography(receipts)
    assert result["status"] == "verified"
    assert result["verified_subject_countries"] == ["AU"]


def test_subject_geography_ignores_unresolvable_ner_places():
    receipts = [
        {"id": 1, "headline": "Estate sells for record sum", "source_name": "R", "places": ["Leuralla"]},
        {"id": 2, "headline": "Historic property changes hands", "source_name": "A", "places": ["Bondi Beach"]},
    ]
    result = infer_receipt_subject_geography(receipts)
    # unresolvable places must not fabricate a country
    assert result["verified_subject_countries"] == []
