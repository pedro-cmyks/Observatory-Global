from app.services.stream_relevance import (
    classify_stream_lane,
    stream_relevance_score,
    score_stream_signal,
)


# --- lane classification ---

def test_crisis_theme_is_analyst_lane():
    assert classify_stream_lane(["CRISISLEX_C03_DEAD_WOUNDED"], "Strike kills 12") == "analyst"


def test_security_category_theme_is_analyst():
    assert classify_stream_lane(["ARMEDCONFLICT"], "Border tensions rise") == "analyst"


def test_sports_headline_is_sports_lane():
    assert classify_stream_lane([], "Vikings 2026 Undrafted Free Agents") == "sports"
    assert classify_stream_lane([], "Aaron Rai leads the golf tournament") == "sports"


def test_entertainment_headline_is_entertainment_lane():
    assert classify_stream_lane([], "Eurovision Song Contest 2026 lineup revealed") == "entertainment"
    assert classify_stream_lane([], "Michael Jackson biopic trailer drops") == "entertainment"


def test_analyst_theme_overrides_sports_headline():
    # A crisis theme present means analyst even if headline reads sporty.
    assert classify_stream_lane(["CRISISLEX_C03_DEAD_WOUNDED"], "Stadium attack during match") == "analyst"


def test_generic_headline_is_general_lane():
    assert classify_stream_lane([], "Company announces quarterly update") == "general"


# --- relevance score ---

def test_analyst_scores_higher_than_sports():
    analyst = stream_relevance_score(["CRISISLEX_C03_DEAD_WOUNDED"], "Strike kills 12")
    sports = stream_relevance_score([], "Vikings undrafted free agents")
    assert analyst > sports


def test_score_is_bounded_zero_to_one():
    s = stream_relevance_score(["CRISISLEX_C03_DEAD_WOUNDED"], "x")
    assert 0.0 <= s <= 1.0


def test_entertainment_scores_low():
    assert stream_relevance_score([], "Eurovision Song Contest 2026") < 0.3


# --- combined helper used by the router ---

def test_score_stream_signal_returns_lane_and_score():
    out = score_stream_signal(["CRISISLEX_C03_DEAD_WOUNDED"], "Strike kills 12")
    assert out["lane"] == "analyst"
    assert 0.0 <= out["relevanceScore"] <= 1.0


def test_score_stream_signal_handles_none_headline():
    out = score_stream_signal([], None)
    assert out["lane"] == "general"


def test_lifestyle_travel_headline_is_lifestyle_lane():
    # 2026-06-29: the "Las Vegas Travel Guide ranks #1" pathology (spec §4.0).
    assert classify_stream_lane([], "Las Vegas Travel Guide") == "lifestyle"
    assert classify_stream_lane([], "10 best restaurants in Rome") == "lifestyle"
    assert classify_stream_lane([], "The ultimate guide to a Tokyo getaway") == "lifestyle"


def test_real_news_label_is_not_demoted_to_a_noise_lane():
    # Real-news labels carry no sports/lifestyle keyword -> general (no penalty).
    assert classify_stream_lane([], "Iran Attacks Bahrain and Kuwait Following US Strikes") == "general"
    assert classify_stream_lane([], "Ukraine War Updates") == "general"
    assert classify_stream_lane([], "Venezuela Earthquake Death Toll Rises") == "general"
