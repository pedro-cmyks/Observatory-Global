"""#248 item 2 — evidence-level lane damp inside crisis threads.

The #246 lifestyle damp ranks whole THREADS; this orders the receipts INSIDE
a crisis-relevant thread so a lifestyle/sports/entertainment article can never
surface as the lead evidence of a serious mega-thread. Damp, never drop:
every receipt still serves, order within each class is preserved.
"""
from app.services.thread_intelligence import order_crisis_evidence


def _row(headline, themes=None):
    return {"headline": headline, "themes": themes or []}


CRISIS = _row("Airstrike kills 12 in border town", ["CRISISLEX_T03_DEAD"])
NEUTRAL = _row("Parliament debates budget amendments")
SPORTS = _row("Premier League transfer window heats up")
ENTERTAINMENT = _row("Ek Hota Maalin tops the box office in its opening week")
LIFESTYLE = _row("Ultimate travel guide: hidden gems for a weekend break")


def test_crisis_thread_sinks_noise_lanes_to_the_tail():
    rows = [SPORTS, CRISIS, ENTERTAINMENT, NEUTRAL, LIFESTYLE]
    ordered = order_crisis_evidence(rows, True)
    assert ordered == [CRISIS, NEUTRAL, SPORTS, ENTERTAINMENT, LIFESTYLE]


def test_damp_never_drop_every_receipt_survives():
    rows = [SPORTS, ENTERTAINMENT, LIFESTYLE]
    ordered = order_crisis_evidence(rows, True)
    assert sorted(r["headline"] for r in ordered) == sorted(r["headline"] for r in rows)


def test_non_crisis_and_untyped_threads_keep_their_order():
    rows = [LIFESTYLE, CRISIS, SPORTS]
    # a lifestyle thread's lifestyle receipts ARE its story, not noise
    assert order_crisis_evidence(rows, False) == rows
    # untyped (crisis_relevant NULL) never damps — absence over guess
    assert order_crisis_evidence(rows, None) == rows


def test_analyst_themes_override_a_sporty_headline():
    # a stadium attack with crisis themes must NOT sink for sounding like sport
    stadium = _row("World Cup stadium stampede kills 12", ["CRISISLEX_T03_DEAD"])
    ordered = order_crisis_evidence([SPORTS, stadium], True)
    assert ordered[0] is stadium


def test_stable_within_each_class():
    n1, n2 = _row("First analyst story"), _row("Second analyst story")
    s1 = _row("playoff picture, week one")
    s2 = _row("playoff picture, week two")
    ordered = order_crisis_evidence([s1, n1, s2, n2], True)
    assert ordered == [n1, n2, s1, s2]


def test_html_encoded_headline_is_decoded_before_lane_matching():
    enc = _row("Premier League&#x20;transfer gossip")
    ordered = order_crisis_evidence([enc, NEUTRAL], True)
    assert ordered == [NEUTRAL, enc]
