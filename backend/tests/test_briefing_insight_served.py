"""End to end over the wire: what goes INTO the paragraph, what comes OUT.

The sibling file (test_briefing_insight_prompt.py) freezes the prompt by
reading the source. This one runs the endpoint against a fake pool and a fake
model, so the two re-judge witnesses are pinned as strings a reader would see:

  IN  — the theme bullet must carry no database code (the model can only write
        "Crisislexrec" if we hand it "Crisislexrec");
  OUT — a paragraph that claims a scale of "−0.48…−0.48" is served with the
        real bounds, because the bounds are constants and not the model's to
        choose.
"""

import pytest

import app.main_v2  # noqa: F401 — the router imports the app; import it first
from app.routers import briefing as B

WITNESS_OUT = "The overall average tone was −0.48 on the −0.48…−0.48 scale."

STATS = {"total": 65481, "countries": 205, "avg_sent": -4.8}
TOP_COUNTRIES = [
    {"country_code": "US", "name": "United States", "cnt": 9000, "avg_s": -3.1},
    {"country_code": "RU", "name": "Russia", "cnt": 4000, "avg_s": -2.0},
]
# The exact five the judge read back to us.
TOP_THEMES = [
    {"theme": "UNGP_FORESTS_RIVERS_OCEANS", "cnt": 900},
    {"theme": "CRISISLEXREC", "cnt": 800},
    {"theme": "WB_696_PUBLIC_SECTOR_MANAGEMENT", "cnt": 700},
    {"theme": "HISTORIC", "cnt": 600},
    {"theme": "GENERAL_HEALTH", "cnt": 500},
]
CATEGORIES = [
    {"category": "Armed conflict escalation", "topics": 12, "signals": 4754},
    {"category": "Crime & Justice", "topics": 9, "signals": 2670},
]


class FakeConn:
    def __init__(self, categories):
        self.categories = categories

    async def execute(self, *_a, **_k):
        return "SET"

    async def fetchval(self, *_a, **_k):
        return True  # theme_hourly_v2 exists

    async def fetchrow(self, query, *_a, **_k):
        assert "AS avg_sent" in query
        return STATS

    async def fetch(self, query, *_a, **_k):
        if "dynamic_topics" in query:
            return self.categories
        if "theme" in query and "GROUP BY theme" in query:
            return TOP_THEMES
        return TOP_COUNTRIES


class FakePool:
    def __init__(self, categories):
        self.conn = FakeConn(categories)

    def acquire(self):
        conn = self.conn

        class _Ctx:
            async def __aenter__(self):
                return conn

            async def __aexit__(self, *_exc):
                return False

        return _Ctx()


@pytest.fixture
def captured(monkeypatch):
    """Run the endpoint; capture the prompt in, control the paragraph out."""
    box = {}

    def _run(categories, model_text):
        async def fake_generate_insight(system, user, **_kw):
            box["system"] = system
            box["user"] = user
            return model_text, "fake", None, {}

        monkeypatch.setattr(B.db, "pool", FakePool(categories), raising=False)
        monkeypatch.setattr(
            "app.services.insight_llm.generate_insight", fake_generate_insight
        )
        import asyncio

        box["result"] = asyncio.run(B.get_briefing_insight(hours=24))
        return box

    return _run


def test_the_prompt_carries_categories_not_codes(captured):
    box = captured(CATEGORIES, "fine.")
    prompt = box["user"]
    assert "Most-covered Atlas categories" in prompt
    assert "Armed conflict escalation, Crime & Justice" in prompt
    for code_ish in ("UNGP", "Ungp", "CRISISLEXREC", "Crisislexrec", "Historic"):
        assert code_ish not in prompt, f"{code_ish!r} is still handed to the model"


def test_the_prompt_falls_back_to_themes_and_still_drops_the_unnameable(captured):
    """No live category → the chart falls back to By Theme, and so does the prose."""
    box = captured([], "fine.")
    prompt = box["user"]
    assert "Most-covered GDELT themes" in prompt
    assert "Public Sector Management" in prompt
    assert "Forests, Rivers and Oceans" in prompt
    assert "General Health" in prompt
    assert "Crisislexrec" not in prompt
    assert "Historic," not in prompt


def test_no_nameable_theme_means_no_bullet_at_all(captured):
    box = captured([], "fine.")
    monkey_prompt = box["user"]
    assert monkey_prompt.count("Most-covered") == 1


def test_the_scale_bullet_separates_the_bounds_from_the_value(captured):
    prompt = captured(CATEGORIES, "fine.")["user"]
    assert "Tone scale: -1.00 to +1.00, fixed bounds" in prompt
    assert "Average tone across all coverage: -0.48 on that -1..+1 scale" in prompt


def test_the_witness_paragraph_is_repaired_before_it_is_served(captured):
    """The exact sentence the judge quoted, in — the real bounds, out."""
    result = captured(CATEGORIES, WITNESS_OUT)["result"]
    assert result["insight"] == (
        "The overall average tone was −0.48 on the −1 to +1 scale."
    )


def test_healthy_prose_is_served_byte_identical(captured):
    good = (
        "Coverage concentrated on Armed conflict escalation, with an average tone "
        "of −0.48 on the −1 to +1 scale across 205 countries."
    )
    assert captured(CATEGORIES, good)["result"]["insight"] == good
