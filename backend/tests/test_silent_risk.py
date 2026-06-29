"""Silent-risk pure helpers (#172)."""
from app.services.silent_risk import (
    is_noise_title, normalize_title, is_silent_risk, why_silent,
)


def test_noise_titles_rejected():
    for t in ["Main_Page", "Special:Search", "Wikipedia:About", "Portal:Current_events",
              "List_of_films_2026", "Some_Movie_(film)", "Foo_(disambiguation)",
              "wiki.phtml", "Index.php?title=Foo"]:
        assert is_noise_title(t) is True


def test_real_topics_kept():
    for t in ["Iran–Israel_war", "Venezuela_earthquake", "Gustavo_Petro", "COVID-19_pandemic"]:
        assert is_noise_title(t) is False


def test_normalize_title():
    assert normalize_title("Iran_Israel_war") == "Iran Israel war"
    assert normalize_title("Gaza_City_(disambiguation)") == "Gaza City"


def test_silent_risk_threshold():
    assert is_silent_risk(5000, 0) is True
    assert is_silent_risk(5000, 2) is True            # below floor of 3
    assert is_silent_risk(5000, 3) is False           # covered
    assert is_silent_risk(0, 0, min_views=1) is False  # no attention


def test_velocity_gates_silent_risk():
    # Evergreen page (steady views, velocity ~1) with no coverage is NOT silent.
    assert is_silent_risk(5000, 0, velocity=1.0) is False
    # A surging page (velocity >= 2) with no coverage IS silent.
    assert is_silent_risk(5000, 0, velocity=3.5) is True
    # Surging but covered -> not silent.
    assert is_silent_risk(5000, 9, velocity=3.5) is False


def test_why_silent_language_hint():
    # A non-Latin title -> language-barrier explanation.
    assert "language" in why_silent("ガザ地区", None, 0).lower()
    assert why_silent("Iran war", None, 0) == "no media coverage found in window"
    assert "information desert" in why_silent("X", "CD", 0, information_desert=True)
    assert "thinly" in why_silent("Iran war", None, 2)
