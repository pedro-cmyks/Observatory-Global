"""Locks the content-based junk classifier + the must-survive guard list.

The guard cases are the real 2026-07-09 prod topics Pedro named as must-survive
(NATO / Ebola / Ukraine / Heatwave / real World Cup / elections) plus the real
junk grab-bags that were eating ~38% of assigned coverage. If a change to
topic_junk starts flagging a guard case or stops flagging a known grab-bag, these
fail.
"""
from scripts.topic_junk import (
    DUMP_MAX_SOURCES,
    DUMP_MIN_MEMBERS,
    EARNINGS_AUTOGEN_MIN_FRACTION,
    PR_WIRE_MIN_FRACTION,
    SERVICE_CONTENT_MIN_FRACTION,
    classify_topic_junk,
    is_earnings_autogen,
    is_pr_wire_solicitation,
    is_recurring_service_content,
)


# --- junk that MUST be flagged (measured on prod 2026-07-09) ---

def test_grabbag_category_flagged():
    assert classify_topic_junk("Local & Community",
                               "Full list of Welsh beaches crowned best in UK",
                               2021, 44)
    assert classify_topic_junk("Celebrity & Sports Drama",
                               "Celebrity Emotional Statements", 1456, 22)
    assert classify_topic_junk("Other", "CentralAsia roundup", 1529, 16)


def test_mixed_prefix_flagged_even_in_real_category():
    # "Mixed:" is the labeler's own grab-bag marker; catch it even when the typer
    # filed it under a real category.
    r = classify_topic_junk("Business & Markets", "Mixed: UK warnings and recalls", 402, 48)
    assert r and "listicle-label" in r


def test_listicle_labels_flagged():
    assert classify_topic_junk("Sports", "WM 2026 Live Streams", 219, 39)
    assert classify_topic_junk("Sports", "World Cup 2026 Match Schedules", 80, 37)
    assert classify_topic_junk("Celebrity & Entertainment",
                               "Who is Ser Torrhen Manderly? Dan Fogler's new House", 826, 45)


def test_feed_dump_flagged_in_legit_category():
    # few-source gravity wells the typer trusted (Indonesian antaranews dump,
    # Korean k-pop mislabeled "AI Policy", single-outlet festival feed).
    assert classify_topic_junk("Crime and Accidents", "Diduga Tenggelam di Sungai Musi", 1607, 5)
    assert classify_topic_junk("AI Industry and Policy", "통신3사 AI 경영", 1879, 7)
    assert classify_topic_junk("Cultural Events and Festivals", "Marcha para Jesus", 1222, 5)


# --- must-survive real stories (guard) ---

def test_guard_real_stories_survive():
    guard = [
        ("Armed conflict escalation", "NATO Summit in Ankara", 778, 12),
        ("Labor strike disruption", "DR Congo Ebola health workers strike over pay", 672, 47),
        ("Armed conflict escalation", "Ukraine War Updates", 589, 19),
        ("Armed conflict escalation", "US-Iran strikes on Bahrain and Kuwait", 524, 33),
        ("Heat and public health risk", "Heatwave Impacts and Disasters", 682, 24),
        ("World Cup 2026", "World Cup 2026 Results", 64, 56),
        ("World Cup 2026", "Morocco World Cup 2026", 52, 19),
        ("Election legitimacy dispute", "Marine Le Pen 2027 presidential bid", 284, 48),
        ("Corruption investigation", "Senegal Political Turmoil", 70, 46),
        # legit non-crisis news is NOT junk
        ("Politics & Governance", "Germany Policy Changes", 196, 19),
        ("Business & Markets", "Financial Market Movements", 198, 30),
    ]
    for cat, label, mem, nsrc in guard:
        assert classify_topic_junk(cat, label, mem, nsrc) is None, f"false-positive: {label}"


# --- boundary behaviour ---

def test_feed_dump_needs_both_size_and_few_sources():
    # small few-source story: NOT a dump (spares genuine regional news)
    assert classify_topic_junk("Crime and Accidents", "Local court ruling", 40, 3) is None
    # large but well-sourced: NOT a dump
    assert classify_topic_junk("Crime and Accidents", "Major event", 900, 30) is None
    # exactly at the floors
    assert classify_topic_junk("Crime and Accidents", "x", DUMP_MIN_MEMBERS, DUMP_MAX_SOURCES)
    assert classify_topic_junk("Crime and Accidents", "x", DUMP_MIN_MEMBERS - 1, DUMP_MAX_SOURCES) is None
    assert classify_topic_junk("Crime and Accidents", "x", DUMP_MIN_MEMBERS, DUMP_MAX_SOURCES + 1) is None


def test_missing_source_count_skips_dump_rule():
    # None distinct_sources: category/label still apply, dump rule skipped
    assert classify_topic_junk("Crime and Accidents", "plain headline", 5000, None) is None
    assert classify_topic_junk("Other", "plain headline", 5000, None)


# --- PR-wire attorney-solicitation class (2026-08-03 TF-3b gate-(c) census) ---
# 15 promoted topics served pr-inside.com law-firm plaintiff-solicitation spam
# (witnesses dt-34 / dt-1626 / dt-4656). All three existing rules were blind:
# the spam grew its own honest-sounding category ("Securities Class Actions" —
# not in JUNK_CATEGORIES), the labels carry no listicle marker, and the revived
# topics hold 1-13 members (feed-dump floor is 150). New signal: fraction of
# sampled receipts that are PR-wire domain + attorney-solicitation headline.

def test_pr_wire_solicitation_signal_matches_witness_receipts():
    # real receipts from dt-34 / dt-1626 / dt-4656 (2026-08-03 prod)
    cases = [
        ("pr-inside.com", None,
         "Levi & Korsinsky Urges PicS N.V. (PICS) Shareholders to Act Before Deadline"),
        ("pr-inside.com", None,
         "Did You Lose Money on Planet Fitness, Inc. (PLNT)? Levi & Korsinsky Reminds Investors"),
        ("pr-inside.com", None,
         "Investor Alert: Deadline Approaching to Join ZoomInfo Technologies Class Action"),
        ("pr-inside.com", None,
         "Contact Levi & Korsinsky by August 4, 2026 to Join Class Action Against Badger Meter"),
        ("pr-inside.com", None,
         "$MSFT Stock Loss: Microsoft May Have Misrepresented Its Business"),
        ("pr-inside.com", None,
         "SHAREHOLDER ALERT: Pomerantz Law Firm Investigates Claims On Behalf of Investors"),
        # syndicated boilerplate on another wire domain still counts
        ("prnewswire.com", None,
         "ROSEN, A LEADING LAW FIRM, Encourages Investors With Losses to Secure Counsel"),
        # domain evidence may live in the URL when source_name is a display name
        ("PR Inside", "https://www.pr-inside.com/investor-alert-deadline-r5262",
         "Investor Alert: Kessler Topaz Reminds Shareholders of Lead Plaintiff Deadline"),
    ]
    for src, url, headline in cases:
        assert is_pr_wire_solicitation(src, url, headline), headline


def test_pr_wire_domain_without_solicitation_headline_is_not_spam():
    # PR wires also carry ordinary corporate releases — domain alone never fires
    assert not is_pr_wire_solicitation(
        "prnewswire.com", None, "Acme Corp Opens New Plant in Ohio")
    assert not is_pr_wire_solicitation(
        "pr-inside.com", None, "Quarterly results show revenue growth")


def test_solicitation_words_on_real_outlet_are_not_spam():
    # genuine class-action NEWS from a real outlet must never count as PR spam
    assert not is_pr_wire_solicitation(
        "reuters.com", None, "Tesla shareholders win class action over Musk pay")
    assert not is_pr_wire_solicitation(
        "nytimes.com", "https://nytimes.com/x", "Investors sue bank in securities fraud case")


def test_pr_wire_fraction_flags_witness_topics():
    # dt-34: 10/13 solicitation receipts; category/label/dump rules all blind
    r = classify_topic_junk("Securities Class Actions", "Levi & Korsinsky Class Actions",
                            13, 3, pr_wire_fraction=10 / 13)
    assert r and "pr-wire" in r
    # dt-1626
    r = classify_topic_junk("Securities Class Actions", "Securities Class Actions",
                            12, 3, pr_wire_fraction=10 / 12)
    assert r and "pr-wire" in r
    # dt-4656: a single receipt that IS the spam
    r = classify_topic_junk("Business & Markets", "Class Action Deadlines",
                            1, 1, pr_wire_fraction=1.0)
    assert r and "pr-wire" in r


def test_pr_wire_fraction_below_threshold_or_missing_is_skipped():
    assert classify_topic_junk("Business & Markets", "Financial Market Movements",
                               198, 30, pr_wire_fraction=0.2) is None
    assert classify_topic_junk("Business & Markets", "Financial Market Movements",
                               198, 30, pr_wire_fraction=None) is None
    # boundary: exactly at the floor fires
    assert classify_topic_junk("Business & Markets", "x",
                               10, 5, pr_wire_fraction=PR_WIRE_MIN_FRACTION)


def test_guard_real_stories_survive_with_zero_pr_wire():
    # the existing must-survive guard, now with the new signal present-and-clean
    assert classify_topic_junk("Armed conflict escalation", "NATO Summit in Ankara",
                               778, 12, pr_wire_fraction=0.0) is None
    assert classify_topic_junk("Business & Markets", "Financial Market Movements",
                               198, 30, pr_wire_fraction=0.0) is None


# --- recurring service-content class (2026-08-04 fresh-cohort re-census) ---
# Calendar-driven posts published daily regardless of events. Witnesses:
# dt-633 (daily Saudi riyal / gold-price posts from Egyptian SEO outlets +
# Friday-prayer duas), dt-4013 (analyst rating reiterations), dt-6485 (budget
# 5G phone spec listicles), dt-1577 (chemical production-cost boilerplate).
# Measured 2026-08-04 (court-scoped receipts, witnesses vs 30 random actives):
# witnesses 88-100% of receipts match, all 30 random topics 0%. Every family
# requires BOTH halves so a pattern alone never kills genuine news.

def test_daily_rate_receipts_match_witnesses():
    # real receipts from dt-633 (2026-08-04 prod): rate-word + today-word +
    # weekday/date — the full calendar enumeration is the service signature
    cases = [
        "سعر الريال السعودي اليوم الجمعة 31-7-2026 في البنوك",
        "أسعار الذهب اليوم الاثنين في السعودية",
        "تراجع سعر الريال السعودي  اليوم الأحد 2 أغسطس 2026",
        "استقرار سعر الريال السعودي اليوم الخميس 30 يوليو 2026.. تعرف إلى أسعار جميع البنوك",
        "أسعار الذهب في السعودية اليوم الثلاثاء",
        # same shape in Spanish (corpus-verified live receipt, laprovincia.es)
        "El precio de la gasolina y diésel hoy sábado 1 de agosto: las gasolineras más baratas",
        # cotización variant (live receipt from dt-1329, elpais.com.uy)
        "Unidad Indexada hoy: cuánto cotiza la UI este martes 4 de agosto de 2026 en pesos uruguayos",
        "Precio del dólar hoy en República Dominicana: martes 4 de agosto de 2026",
        # and in English (maharashtratimes.com live receipt)
        "Gold Silver Rate Hike Today 3 August 2026",
    ]
    for h in cases:
        assert is_recurring_service_content(h), h


def test_price_news_is_not_service_content():
    # a price MOVE tied to an event is news; both-halves discipline means the
    # rate-word alone (or with a bare "today") never fires
    for h in [
        "Oil price crashes after OPEC decision",
        "Gold prices surge today as dollar weakens",
        "Egypt central bank raises interest rates on Thursday",
        # rate-word + weekday but no today-word: market commentary, not service
        "The Fed Didn't Raise Rates Wednesday – So Why Did the Market Plunge?",
        "Precio del dólar repunta tras el anuncio de aranceles",
        "La bolsa de Buenos Aires cotiza en alza tras el acuerdo comercial",
    ]:
        assert not is_recurring_service_content(h), h


def test_prayer_horoscope_lottery_calendars_match():
    # dt-633 receipts include Friday-prayer duas; horoscope/lottery same class
    cases = [
        "دعاء الصباح اليوم الجمعة 31-7-2026.. أفضل الأدعية المستحبة لبدء يوم الجمعة بالخير والبركة",
        "Aries Horoscope Today, August 1, 2026: Keep your expectations realistic",
        "Horóscopo de hoy, martes 04 de agosto: las predicciones para la salud",
        "Kerala Lottery Result Today 4 August 2026: Sthree Sakthi SS-400 winners",
        # Spanish lottery draws (live receipts from dt-1329)
        "Sorteo de la Lotería de México: números ganadores de hoy lunes, 3 de agosto de 2026",
        "Resultados Super Astro Luna de hoy: números ganadores del último sorteo del lunes 3 de agosto",
    ]
    for h in cases:
        assert is_recurring_service_content(h), h
    # calendar word in a NEWS context (no calendar enumeration) never fires
    assert not is_recurring_service_content(
        "Lottery winner sues state over unpaid jackpot")
    assert not is_recurring_service_content(
        "Detienen al organizador del sorteo fraudulento en Madrid")


def test_rating_reiteration_boilerplate_matches_witnesses():
    # real receipts from dt-4013 (2026-08-04 prod) — MarketBeat-network shapes
    cases = [
        'Deutsche Bank Aktiengesellschaft Reiterates "Buy" Rating for NatWest Group (LON:NWG)',
        "Unite Group (LON:UTG) Given Hold Rating at Jefferies Financial Group",
        "Greggs' (GRG) Sell Rating Reiterated at Deutsche Bank Aktiengesellschaft",
        "Lloyds Banking Group (LON:LLOY) Receives Buy Rating from Jefferies Financial Group",
        'NatWest Group\'s (NWG) "Buy" Rating Reaffirmed at Jefferies Financial Group',
        "dotdigital Group (LON:DOTD) Earns \"Buy\" Rating from Canaccord Genuity Group",
        "London Stock Exchange Group (LON:LSEG) Given Outperform Rating at Royal Bank Of Canada",
        "QXO (QXO) – Research Analysts' Weekly Ratings Changes",
        "O-I Glass (OI) – Research Analysts' Weekly Ratings Updates",
        "Recent Analysts' Ratings Changes for BrightSpring Health Services (BTSG)",
        "Zacks Research Maintains $12.50 Price Target for Vodafone",
    ]
    for h in cases:
        assert is_recurring_service_content(h), h


def test_agency_rating_news_is_not_service_content():
    # sovereign / agency rating NEWS must never fire (different vocabulary:
    # affirms/downgrades, no brokerage grade-word next to "rating")
    for h in [
        "Fitch affirms US AAA rating",
        "S&P downgrades France's credit rating on debt concerns",
        "Moody's maintains negative outlook on French banks",
        "EU watchdog investigates credit rating agencies",
    ]:
        assert not is_recurring_service_content(h), h


def test_production_cost_report_boilerplate_matches_witnesses():
    # real receipts from dt-1577 (briefingwire.com SEO report mill)
    cases = [
        "Calcium Cyanamide Production Cost, Analysis & Breakdown",
        "Calcium Iodate Production Cost | Cost Analysis & Breakdown",
        "Calcium Lactate Price Trend 2026: Market Analysis, Drivers, Forecast",
        "Bosentan Production Cost, Cost Analysis & Breakdown",
    ]
    for h in cases:
        assert is_recurring_service_content(h), h
    # production costs in a NEWS sentence never fire
    assert not is_recurring_service_content(
        "EV production cost falls as battery prices drop")
    assert not is_recurring_service_content(
        "Farmers protest rising production costs across France")


def test_gadget_spec_listicles_match_witnesses():
    # real receipts from dt-6485: mAh battery-spec numbers + multi-way "vs"
    # spec comparisons (both carry model/spec digits by construction)
    cases = [
        "OnePlus का 7,000 mAh बैटरी वाला नया 5G फोन लॉन्च, सस्ते में मिलेगा",
        "6500mAh ব্যাটারি সহ সস্তা iQOO 5G ফোনের সেল আগামীকাল",
        "OnePlus N6x vs iQOO Z11 Lite vs Realme Narzo 100x 5G: ডিসপ্লে, প্রসেসর তুলনা",
        "Vivo T5e vs Samsung Galaxy M17e 5G vs Realme P4 Lite 5G: 16 হাজার টাকার বাজেটে",
    ]
    for h in cases:
        assert is_recurring_service_content(h), h


def test_gadget_needs_spec_shape():
    # plain product news / digit-free comparisons never fire
    for h in [
        "Apple launches iPhone 17 with satellite messaging",
        "Singapore vs Hong Kong vs Dubai: Regional HQ Trade-Offs for Investors",
        "Samsung and Apple battle for the budget 5G market",
        "Nottm Forest vs Blackburn Rovers preview",
    ]:
        assert not is_recurring_service_content(h), h


def test_service_content_handles_none_and_entities():
    assert not is_recurring_service_content(None)
    assert not is_recurring_service_content("")
    # HTML-entity-encoded quotes still match (the #264 lesson)
    assert is_recurring_service_content(
        "Deutsche Bank Reiterates &quot;Buy&quot; Rating for NatWest Group")


def test_service_fraction_flags_witness_topics():
    # dt-633: 11/11 receipts are daily-rate/dua posts; every other rule blind
    # (category "Currency & Fiscal Policy", no listicle label, 11 members)
    r = classify_topic_junk("Currency & Fiscal Policy", "Saudi Riyal and Gold Prices",
                            11, 4, service_fraction=1.0)
    assert r and "service-content" in r
    # dt-4013: 22/22 rating reiterations in an honest-sounding category
    r = classify_topic_junk("Business & Markets", "Analyst Rating Reiterations",
                            22, 3, service_fraction=1.0)
    assert r and "service-content" in r
    # dt-6485: 7/8 gadget listicles
    r = classify_topic_junk("Science & Technology", "Budget 5G Smartphone Launches",
                            8, 3, service_fraction=7 / 8)
    assert r and "service-content" in r
    # dt-1577: 18/18 production-cost boilerplate
    r = classify_topic_junk("Business & Markets", "Chemical Production Cost Analysis",
                            18, 1, service_fraction=1.0)
    assert r and "service-content" in r


def test_service_fraction_below_threshold_or_missing_is_skipped():
    assert classify_topic_junk("Business & Markets", "Financial Market Movements",
                               198, 30, service_fraction=0.2) is None
    assert classify_topic_junk("Business & Markets", "Financial Market Movements",
                               198, 30, service_fraction=None) is None
    # boundary: exactly at the floor fires
    assert classify_topic_junk("Business & Markets", "x",
                               10, 5, service_fraction=SERVICE_CONTENT_MIN_FRACTION)


def test_guard_real_stories_survive_with_zero_service_fraction():
    assert classify_topic_junk("Armed conflict escalation", "NATO Summit in Ankara",
                               778, 12, pr_wire_fraction=0.0,
                               service_fraction=0.0) is None
    assert classify_topic_junk("Business & Markets", "Financial Market Movements",
                               198, 30, pr_wire_fraction=0.0,
                               service_fraction=0.0) is None


# --- EARNINGS-AUTOGEN class (2026-08-04, witness dt-9420) ---
# Quarterly-report robo-posts: the MarketBeat autogen network (tickerreport /
# themarketsdaily / dailypolitical — same network as dt-4013's ratings) plus
# the boilerplate shapes it syndicates (AP "Q2 Earnings Snapshot" robots, fool/
# yahoo "Earnings Call Transcript" series, press-release results templates).
# Measured 2026-08-04 (union receipt lane, witness + 33 earnings-labeled active
# siblings vs 30 random actives): autogen cohort 0.50-1.00, every real-news
# earnings topic 0.00-0.38, all 30 random topics 0.00, corpus fire rate
# 16/10,000 = 0.16% with all 16 hand-checked true. Both halves per receipt:
# an earnings pattern alone never fires on real news.

def test_ticker_earnings_boilerplate_matches_witness_receipts():
    # real receipts from dt-9420 / dt-2690 / dt-8648 / dt-8668 (2026-08-04
    # prod): exchange-ticker parenthetical + earnings word = autogen shape,
    # fires with no source information at all
    cases = [
        "Allegro MicroSystems (NASDAQ:ALGM) Issues Earnings Results, Beats Estimates By $0.02 EPS",
        "AltaGas (TSE:ALA) Announces Quarterly Earnings Results",
        "TVA Group (TSE:TVA.B) Announces Quarterly Earnings Results",
        "Melrose Industries (LON:MRO) Releases Quarterly Earnings Results",
        "Chiyoda (OTCMKTS:CHYCY) Posts Quarterly Earnings Results",
        "Terex (NYSE:TEX) Releases FY 2026 Earnings Guidance",
        "AbbVie (NYSE:ABBV) Updates Q3 2026 Earnings Guidance",
        "DXC Technology (NYSE:DXC) Releases Q2 2027 Earnings Guidance",
    ]
    for h in cases:
        assert is_earnings_autogen(None, None, h), h


def test_press_release_results_template_matches():
    # the globenewswire-syndication shape (dt-30 / dt-1949 / dt-8548 receipts):
    # verb + quarter phrase + year/fiscal filler only + "results"
    cases = [
        "Balchem Corporation Reports Second Quarter 2026 Financial Results",
        "FEMSA Announces Second Quarter 2026 Results",
        "Yangarra Announces 2026 Second Quarter Financial and Operating Results",
        "KBR Reports Second Quarter Fiscal 2026 Results",
        # results-before-quarter (reversed) branch
        "Leonardo DRS Announces Financial Results for Second Quarter 2026",
        "Imperial announces second quarter 2026 financial and operating results",
        "Tecogen Schedules Earnings Release Date and Conference Call for Q2 2026 Results",
    ]
    for h in cases:
        assert is_earnings_autogen(None, None, h), h


def test_real_earnings_news_never_fires():
    # THE guard — event-driven earnings journalism (real receipts from
    # dt-4289 / dt-8155 / dt-8539 / dt-8548, the surviving siblings): the
    # quarter->results gap in real sentences carries arbitrary words, "beats
    # estimates" comes without "by $", school results carry no quarter word
    for h in [
        "Apple crushes earnings expectations, stock soars",
        "HSBC beats estimates with US$10.1 billion quarterly profit, announces fresh US$1 billion stock buyback",
        "Kosmos reports 12% production growth in Q2 as GTA, Jubilee drive results",
        "BP's Q2 profit doubles to top US$5 billion on oil surge",
        "Saudi Aramco Reports Net Income of $32.7 Bln in Second Quarter",
        "Rivian Q2 2026: EV Revenue Jumps 27% as R2 Drives Higher Deliveries, Gross Profit and Outlook",
        "Zalando reports lower Q2 net income; narrows full-year guidance",
        "Diamondback Raises 2026 Output Forecast After Production Milestone",
        "Ather Energy shares surge over 16%, hit 52-week high after Q1 results; brokerages bullish",
        "SoftBank's AI Funding Plans to Face Reckoning at Q1 earnings",
        "Nivea Maker Beiersdorf Cuts Guidance For 2026, Citing Difficult Market",
        # calendar RESULTS that are not corporate quarters
        "BISE Peshawar Announces 10th Class Results 2026",
        "ZIMSEC releases 2026 June exam results; O-Level pass rate drops, A-Level performance improves",
    ]:
        assert not is_earnings_autogen(None, None, h), h
        # and a real outlet name never changes the verdict
        assert not is_earnings_autogen("reuters.com", None, h), h


def test_eps_delta_boilerplate_matches():
    # "beats/misses estimates by $X" and "EPS of $X beats/misses" only exist
    # in autogen posts; real coverage writes "beats estimates with ..."
    cases = [
        "Madrigal Pharmaceuticals (NASDAQ:MDGL) Posts Earnings Results, Beats Estimates By $0.69 EPS",
        "Wallbox (NYSE:WBX) Announces Quarterly Earnings Results, Misses Estimates By $0.09 EPS",
        # the ticker-free variant of the same generator (task-named shape)
        "Alamos Gold Q2 Earnings: EPS of $0.32 beats by $0.07",
    ]
    for h in cases:
        assert is_earnings_autogen(None, None, h), h


def test_earnings_calendar_autogen_matches():
    # dt-4576 / dt-9119 receipts: "to Announce/Post/Release (Quarterly)
    # Earnings on <weekday>" — the weekday IS the calendar signature
    cases = [
        "Energy Services of America (ESOA) to Release Quarterly Earnings on Wednesday",
        "Airbnb (ABNB) Expected to Announce Earnings on Thursday",
        "Marathon Digital (MARA) to Post Quarterly Earnings on Thursday",
        "Ultralife (ULBI) Projected to Release Earnings on Friday",
    ]
    for h in cases:
        assert is_earnings_autogen(None, None, h), h
    # no weekday = no calendar signature (real preview coverage survives)
    assert not is_earnings_autogen(
        None, None, "Apple set to report earnings after the bell")


def test_call_series_and_snapshot_match():
    # MarketBeat "Q2 Earnings Call Highlights" + fool/yahoo "Earnings Call
    # Transcript/Summary" + the AP "Q2 Earnings Snapshot" robot series
    cases = [
        "Cameco Q2 Earnings Call Highlights",
        "Stellantis N.V. Q2 2026 Earnings Call Summary",
        "Labcorp (LH) Q2 2026 Earnings Call Transcript",
        "Proto Labs: Q2 Earnings Snapshot",
    ]
    for h in cases:
        assert is_earnings_autogen(None, None, h), h
    # an earnings call as a news EVENT is not the series
    assert not is_earnings_autogen(
        None, None, "Novo Nordisk earnings call: CEO addresses investor concerns")


def test_autogen_domain_half():
    # weak patterns (previews) fire only on the measured network domains —
    # the same headline from a real outlet survives
    assert is_earnings_autogen(
        "tickerreport.com", None, "What to Expect From GE Aerospace's Earnings")
    assert not is_earnings_autogen(
        "cnbc.com", None, "What to expect from Apple's earnings report")
    # domain alone never fires (non-earnings network content is out of scope
    # here — the ratings posts belong to the service-content rule)
    assert not is_earnings_autogen(
        "themarketsdaily.com", None, "Insider Selling at Acme Corp")
    # domain evidence may live in the URL when source_name is a display name
    assert is_earnings_autogen(
        "Ticker Report", "https://www.tickerreport.com/x",
        "GE Aerospace Earnings Preview")


def test_earnings_autogen_handles_none_and_entities():
    assert not is_earnings_autogen(None, None, None)
    assert not is_earnings_autogen("tickerreport.com", None, "")
    # HTML-entity-encoded punctuation still matches (the #264 lesson)
    assert is_earnings_autogen(
        None, None,
        "Greggs&#039; (LON:GRG) Announces Quarterly Earnings Results")


def test_earnings_fraction_flags_witness_topics():
    # dt-9420: 11/12 receipts autogen; category/label/dump/pr-wire/service all
    # blind (honest-sounding category, no listicle label, 12 members)
    r = classify_topic_junk("Corporate Earnings Reports",
                            "Earnings Results Announcements",
                            12, 3, earnings_fraction=11 / 12)
    assert r and "earnings-autogen" in r
    # dt-8668: guidance clone at 1.0
    r = classify_topic_junk("Earnings Guidance", "FY 2026 Earnings Guidance",
                            33, 3, earnings_fraction=1.0)
    assert r and "earnings-autogen" in r
    # dt-9103: the AP snapshot series
    r = classify_topic_junk("Business & Markets", "Q2 Earnings Snapshots",
                            16, 8, earnings_fraction=1.0)
    assert r and "earnings-autogen" in r
    # dt-10057: transcript series at 0.73
    r = classify_topic_junk("Quarterly Earnings Coverage", "Q2 2026 Earnings Calls",
                            75, 12, earnings_fraction=0.73)
    assert r and "earnings-autogen" in r


def test_earnings_fraction_below_threshold_or_missing_is_skipped():
    # dt-4738 measured 0.38 — majority real earnings journalism, survives
    assert classify_topic_junk("Corporate Earnings", "Q2 Profit Rises",
                               45, 20, earnings_fraction=0.38) is None
    assert classify_topic_junk("Business & Markets", "Financial Market Movements",
                               198, 30, earnings_fraction=None) is None
    # boundary: exactly at the floor fires (dt-8723 measured 0.50)
    assert classify_topic_junk("Business & Markets", "x",
                               10, 5,
                               earnings_fraction=EARNINGS_AUTOGEN_MIN_FRACTION)


def test_guard_real_stories_survive_with_zero_earnings_fraction():
    assert classify_topic_junk("Armed conflict escalation", "NATO Summit in Ankara",
                               778, 12, pr_wire_fraction=0.0,
                               service_fraction=0.0,
                               earnings_fraction=0.0) is None
    assert classify_topic_junk("Business & Markets", "Financial Market Movements",
                               198, 30, pr_wire_fraction=0.0,
                               service_fraction=0.0,
                               earnings_fraction=0.0) is None
