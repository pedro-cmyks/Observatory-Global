"""Content-based topic junk classifier (2026-07-09 useful-coverage gate).

The clustering recall fix (9d1b04e7) took story coverage 0.04% -> ~40% but the
relaxed promotion gate admitted JUNK grab-bags as active anchors. Measured on the
2026-07-09 prod unified-v2 state (docs/state/2026-07-09-useful-coverage-gate.md):
25 of 154 served topics are junk and eat 30% of assigned coverage.

WHY NOT the existing signals:
  - cohesion / whitened cohesion: DISPROVED (clustering-recall doc) — grab-bags are
    topically tight; build_unified_topics assigns members at >=0.82 cosine so every
    member is close to the centroid by construction. Junk cohesion is HIGH.
  - noise_rate: does NOT separate ("Celebrity Emotional Statements" 0.74 but
    "Full list of Welsh beaches" 0.27, "Who is Ser Torrhen Manderly?" 0.00).
  - subject_concentration (content-entropy, #224): CONFOUNDED here — Cyrillic/Greek
    morphology and the >=0.82 assign-vacuum drag good events down to junk levels
    (Ukraine 0.12, DR Congo Ebola 0.13 vs Welsh beaches 0.07). Kept upstream for
    single-outlet emergent roundups; unreliable as the primary unified-v2 signal.
  - label regexes alone: 8/597 recall (measured). Too brittle.

WHAT DOES separate (measured 2026-07-09), a UNION of three content signals:
  1. JUNK CATEGORY — the R3.1 DeepSeek typer already made the per-topic
     useful/entertainment/grab-bag judgment; its `category` is the strongest
     separator (Welsh beaches -> "Local & Community", Celebrity -> "Celebrity &
     Sports Drama", the "Mixed:" roundups -> "Daily News Roundups").
  2. LISTICLE / self-declared-grab-bag LABEL — catches listicles the typer put in
     an otherwise-real category ("Mixed: UK warnings and recalls" in Business &
     Markets, "WM 2026 Live Streams" in Sports).
  3. FEED-DUMP by source diversity — a LARGE topic carried by very FEW outlets is
     one outlet's feed dumped into a gravity well (Indonesian antaranews 1607
     members / 5 sources, Korean k-pop mislabeled "AI Policy" 1879/7, "Marcha para
     Jesus" 1222/5). Catches the mislabeled dumps the category typer trusts.

GUARD (must-survive real stories): sports is NOT a junk category — World Cup match
results/updates are real events (Pedro: World Cup must survive; damp in ranking,
not gate). Politics & Governance / Business & Markets / Science & Technology stay
useful. The feed-dump floor (>=150 members AND <=8 sources) never touches genuine
small regional stories. Verified: NATO/Ebola/Ukraine/Heatwave/real-World-Cup/
elections all pass.

Pure + importable by build_unified_topics, project_dynamic_topics, flag_junk_topics.
"""
from __future__ import annotations

import html as _html
import re

# Category vocabulary from the R3.1 typer (scripts/compute_category_typing.py /
# grow_atlas_categories). These are the grab-bag / entertainment-fluff / lifestyle
# / residual buckets — measured against the 2026-07-09 active population as the
# NON-useful classes. Sports*/World Cup*/Football*/Tennis*/Motorsport* are
# deliberately EXCLUDED (real events, damped in ranking not gated). Politics &
# Governance, Business & Markets, Science & Technology, the crisis categories, and
# Cultural Events stay useful (few-source dumps inside them are caught by rule 3).
JUNK_CATEGORIES = frozenset({
    "Daily News Roundups",        # the labeler's own "Mixed: <theme>" grab-bags
    "Celebrity & Sports Drama",
    "Celebrity & Entertainment",
    "Entertainment & Culture",
    "Travel Scams / Lifestyle",
    "Local & Community",          # Welsh-beaches / Köln-pool local roundups
    "Other",                      # typer residual/uncertain bucket (CentralAsia grab-bag)
    "Obituary & Tribute",
})

# High-precision listicle / self-declared-grab-bag markers. "Mixed:" is emitted by
# build_unified_topics' own label prompt for grab-bags (self-declared). Generic
# words ("results", "guide", "explained") are DELIBERATELY excluded — they fire on
# real news ("election results") — the category + dump signals carry the recall.
LISTICLE_LABEL = re.compile(
    r"(^\s*mixed:|\bfull list\b|\bwho is .+\?|\blive stream|\bmatch schedule|"
    r"\bfixtures?\b|\bhow to watch\b|\bwhat time\b|\bwhere to watch\b|"
    r"\bmeet the\b|\blistings?\b|\bhoroscopes?\b|\brecipes?\b|\bstarting (xi|11)\b)",
    re.IGNORECASE,
)

# Feed-dump signature: a topic this LARGE carried by this FEW distinct outlets is
# one source's feed dumped as a gravity well, not a corroborated narrative. Floors
# chosen (measured 2026-07-09): junk dumps sit at 1-7 distinct sources across
# 1000+ members; every real event of comparable size spans >=12 outlets
# (DR Congo Ebola 47, NATO 12, Ukraine 19). The member floor spares genuine small
# regional stories (a 20-member 3-outlet local story is untouched).
DUMP_MIN_MEMBERS = 150
DUMP_MAX_SOURCES = 8

# PR-wire attorney-solicitation class (2026-08-03 TF-3b gate-(c) census): 15
# promoted topics served pr-inside.com law-firm plaintiff-solicitation spam
# ("SHAREHOLDER ALERT" Pomerantz / Levi & Korsinsky boilerplate). All three
# rules above were blind — the spam grew its own honest-sounding category
# ("Securities Class Actions", not in JUNK_CATEGORIES), the labels carry no
# listicle marker, and the revived topics hold 1-13 members (feed-dump floor
# 150). BOTH halves must match per receipt: PR wires also carry ordinary
# corporate releases (domain alone never fires), and real outlets cover genuine
# class actions (solicitation words alone never fire).
PR_WIRE_DOMAINS = re.compile(
    r"(pr-inside\.com|prnewswire|businesswire|globenewswire|accesswire|"
    r"newsfilecorp|briefingwire)",
    re.IGNORECASE,
)
ATTORNEY_SOLICITATION = re.compile(
    r"(shareholder alert|investor alert|class action|lead plaintiff|"
    r"securities fraud|stock loss|los[te] money on|"
    r"reminds? investors|encourages? investors|"
    r"urges? (?:\S+\s+){0,6}(shareholders|investors)|"
    r"pomerantz|levi\s*&\s*korsinsky|rosen law|bronstein|glancy|kessler topaz|"
    r"robbins geller|kahn swick|schall law|portnoy law|hagens berman|faruqi)",
    re.IGNORECASE,
)
# Junk when at least half the sampled receipts are solicitation spam. Witness
# topics sit at 0.77-1.0; a real securities story with genuine outlet coverage
# dilutes the fraction well below the floor.
PR_WIRE_MIN_FRACTION = 0.5

# Recurring SERVICE-CONTENT class (2026-08-04 fresh-cohort re-census): posts
# published on a CALENDAR, not on events — daily exchange-rate/gold-price
# posts (Egyptian SEO outlets), Friday-prayer duas, brokerage rating
# reiterations (the MarketBeat autogen network), budget-gadget spec
# listicles, and SEO production-cost/price-trend report mills. Witnesses
# dt-633 / dt-4013 / dt-6485 / dt-1577; category/label/dump/pr-wire rules all
# blind (honest-sounding categories, no listicle label, 8-22 members).
# Measured on court-scoped receipts (witnesses vs 30 random actives,
# docs/research + this module's shipping run): witnesses 88-100% of receipts
# match, ALL 30 random topics 0%, corpus-wide fire rate ~0.1% and true.
# BOTH-halves discipline per family — a pattern alone never kills real news:
#   A daily-rate: rate-word AND today-word AND weekday/date. "Oil price
#     crashes after OPEC decision" (no calendar) and "The Fed Didn't Raise
#     Rates Wednesday" (no today-word) never fire; the service posts always
#     enumerate the calendar ("سعر الريال اليوم الجمعة 31-7-2026").
#   B calendar content: prayer/horoscope/lottery word AND calendar mark.
#     "Lottery winner sues state" never fires.
#   C rating boilerplate: brokerage GRADE word inside the rating phrase.
#     Agency news ("Fitch affirms AAA", "S&P downgrades France") never fires.
#   D report mill: "Production Cost"/"Price Trend" + analysis/breakdown/
#     forecast boilerplate. "EV production cost falls" never fires.
#   E gadget spec: mAh spec-number, or a 3-way "vs" comparison carrying a
#     digit (model numbers). "Singapore vs Hong Kong vs Dubai" never fires.
_SVC_RATE_WORD = re.compile(
    r"(\bprices?\b|\brates?\b|\bprecios?\b|\bcotizaci[oó]n\b|\bcotiza\b|"
    r"سعر|أسعار|اسعار)", re.IGNORECASE)
_SVC_TODAY = re.compile(r"(\btoday\b|\bhoy\b|اليوم)", re.IGNORECASE)
_SVC_WEEKDAY = re.compile(
    r"(\bmonday\b|\btuesday\b|\bwednesday\b|\bthursday\b|\bfriday\b|"
    r"\bsaturday\b|\bsunday\b|"
    r"\blunes\b|\bmartes\b|\bmi[eé]rcoles\b|\bjueves\b|\bviernes\b|"
    r"\bs[aá]bado\b|\bdomingo\b|"
    r"الاثنين|الإثنين|الثلاثاء|الأربعاء|الاربعاء|الخميس|الجمعة|السبت|الأحد|الاحد)",
    re.IGNORECASE)
_SVC_NUM_DATE = re.compile(r"\b\d{1,2}\s*[-/]\s*\d{1,2}\s*[-/]\s*\d{2,4}\b")
_SVC_MONTH_DATE = re.compile(
    r"\b\d{1,2}\s+(january|february|march|april|may|june|july|august|"
    r"september|october|november|december|"
    r"enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|"
    r"noviembre|diciembre|"
    r"يناير|فبراير|مارس|أبريل|ابريل|مايو|يونيو|يوليو|أغسطس|اغسطس|سبتمبر|"
    r"أكتوبر|اكتوبر|نوفمبر|ديسمبر)",
    re.IGNORECASE)
_SVC_CAL_WORD = re.compile(
    r"(دعاء|أدعية|الأدعية|horoscopes?\b|hor[oó]scopos?\b|rashifal|राशिफल|"
    r"panchang|पंचांग|lottery results?|lotto results?|"
    r"\bsorteo\b|\bloter[ií]a\b|n[uú]meros ganadores)", re.IGNORECASE)
_SVC_GRADE = (
    r"(buy|sell|hold|outperform|underperform|overweight|underweight|neutral|"
    r"market perform|sector perform|moderate buy|strong[- ]buy|positive)")
_SVC_RATING_BOILER = re.compile(
    r"((reiterat|reaffirm)\w*\s+[\"“']?" + _SVC_GRADE + r"[\"”']?\s+rating|"
    + _SVC_GRADE + r"[\"”']?\s+rating\s+(reiterated|reaffirmed)\b|"
    r"(given|receives?|earns?)\s+[\"“']?" + _SVC_GRADE +
    r"[\"”']?\s+rating\s+(at|from)\b|"
    r"maintains?\s+.{0,30}price\s+target|"
    r"analysts['’]?\s+(weekly\s+|recent\s+)?ratings?\s+(changes|updates))",
    re.IGNORECASE)
_SVC_REPORT_BOILER = re.compile(
    r"(production\s+cost\W{0,8}.{0,30}(analysis|breakdown|report)|"
    r"price\s+trend\s+20\d\d|price\s+trend\W{0,4}.{0,40}(analysis|forecast))",
    re.IGNORECASE)
_SVC_MAH = re.compile(r"\d[\d,.٫٬]*\s*mAh", re.IGNORECASE)
_SVC_DOUBLE_VS = re.compile(r"\svs\.?\s.{1,80}\svs\.?\s", re.IGNORECASE)
_SVC_DIGIT = re.compile(r"\d")
# Junk when at least half the sampled receipts are service content (mirrors
# PR_WIRE_MIN_FRACTION). Witnesses sit at 0.88-1.0; every random-30 topic
# measured 0.0, so a real story with one calendar-shaped receipt never nears
# the floor.
SERVICE_CONTENT_MIN_FRACTION = 0.5


def is_recurring_service_content(headline: str | None) -> bool:
    """One receipt = calendar-driven service content (see family comments)."""
    if not headline:
        return False
    h = _html.unescape(headline)
    calendar_mark = (
        _SVC_WEEKDAY.search(h) or _SVC_NUM_DATE.search(h)
        or _SVC_MONTH_DATE.search(h))
    if _SVC_RATE_WORD.search(h) and _SVC_TODAY.search(h) and calendar_mark:
        return True  # A daily-rate
    if _SVC_CAL_WORD.search(h) and (calendar_mark or _SVC_TODAY.search(h)):
        return True  # B prayer/horoscope/lottery calendar
    if _SVC_RATING_BOILER.search(h):
        return True  # C brokerage rating boilerplate
    if _SVC_REPORT_BOILER.search(h):
        return True  # D production-cost / price-trend report mill
    if _SVC_MAH.search(h) or (_SVC_DOUBLE_VS.search(h) and _SVC_DIGIT.search(h)):
        return True  # E gadget spec listicle
    return False


def is_pr_wire_solicitation(
    source_name: str | None,
    source_url: str | None,
    headline: str | None,
) -> bool:
    """One receipt = PR-wire domain (name or url) AND solicitation headline."""
    hay = f"{source_name or ''} {source_url or ''}"
    if not PR_WIRE_DOMAINS.search(hay):
        return False
    return bool(headline and ATTORNEY_SOLICITATION.search(_html.unescape(headline)))


def classify_topic_junk(
    category: str | None,
    label: str | None,
    member_count: int,
    distinct_sources: int | None,
    pr_wire_fraction: float | None = None,
    service_fraction: float | None = None,
) -> str | None:
    """Return a semicolon-joined junk reason, or None if the topic is useful.

    distinct_sources is the count over a sample of the topic's assigned members
    (unified-v2); pass None when unavailable (then the feed-dump rule is skipped —
    the category/label rules still apply). pr_wire_fraction is the share of that
    same sample matching is_pr_wire_solicitation; None skips the PR-wire rule.
    service_fraction is the share matching is_recurring_service_content; None
    skips the service-content rule.
    """
    reasons: list[str] = []
    if category and category in JUNK_CATEGORIES:
        reasons.append(f"category:{category}")
    if label and LISTICLE_LABEL.search(_html.unescape(label)):
        reasons.append("listicle-label")
    if (
        distinct_sources is not None
        and member_count >= DUMP_MIN_MEMBERS
        and distinct_sources <= DUMP_MAX_SOURCES
    ):
        reasons.append(f"feed-dump:{distinct_sources}src/{member_count}mem")
    if pr_wire_fraction is not None and pr_wire_fraction >= PR_WIRE_MIN_FRACTION:
        reasons.append(f"pr-wire-solicitation:{pr_wire_fraction:.0%}")
    if (
        service_fraction is not None
        and service_fraction >= SERVICE_CONTENT_MIN_FRACTION
    ):
        reasons.append(f"service-content:{service_fraction:.0%}")
    return ";".join(reasons) if reasons else None
