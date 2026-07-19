"""#248 discussion-attach relevance honesty (community-discussion lane, #237).

The lane attaches social posts to a topic at a fixed semantic threshold and
used to serve them with NO relevance signal — an off-topic hobby post attached
at 0.90 rendered identically to a genuine claim-origin post (the Mbappé/
Pasta-Grannies class). Honesty contract:

  * every item carries its MEASURED attach `similarity` (tm.confidence) when
    the engine recorded one — absent (never faked) when it did not;
  * hobby/sports/entertainment/lifestyle posts carry a `lane` tag and are
    DAMPED to the bottom, never dropped (no silent filtering);
  * the payload reports how many items are noise-tagged (`noise_count`).
"""
from app.services.community_discussion import build_discussion_items


def _row(headline, source_name="lemmy/worldnews@lemmy.world", confidence=0.91,
         origin="US", country="US", lang="en", ts=None):
    return {
        "headline": headline,
        "source_name": source_name,
        "source_url": "https://example.org/p/1",
        "source_lang": lang,
        "source_origin_country": origin,
        "country_code": country,
        "timestamp": ts,
        "confidence": confidence,
    }


def test_items_carry_measured_similarity():
    items = build_discussion_items([_row("Strikes hit Kharkiv overnight", confidence=0.9312)])
    assert items[0]["similarity"] == 0.9312
    # invariant stamps survive
    assert items[0]["verified"] is False
    assert items[0]["role"] == "discussion"


def test_missing_confidence_is_absent_not_faked():
    items = build_discussion_items([_row("Strikes hit Kharkiv overnight", confidence=None)])
    assert "similarity" not in items[0]


def test_hobby_community_gets_lane_tag_and_damps_below_news():
    rows = [
        _row("Little wolf girl I made my daughter",
             source_name="lemmy/crochet@lemmy.ca", confidence=0.95),
        _row("Israel and Lebanon reach draft agreement", confidence=0.90),
    ]
    items = build_discussion_items(rows)
    # News-y discussion first even though the hobby post attached higher.
    assert items[0]["headline"].startswith("Israel")
    assert "lane" not in items[0]
    assert items[1]["lane"] == "hobby"
    # Damp, never gate: both still served.
    assert len(items) == 2


def test_order_within_groups_is_preserved():
    rows = [
        _row("first news"), _row("second news"),
        _row("My first sourdough finally worked", confidence=0.88),
        _row("third news"),
    ]
    items = build_discussion_items(rows)
    assert [i["headline"] for i in items] == [
        "first news", "second news", "third news",
        "My first sourdough finally worked",
    ]


def test_html_entities_decoded():
    items = build_discussion_items([_row("Ukraine &#x2014; strikes &amp; talks")])
    assert items[0]["headline"] == "Ukraine — strikes & talks"


def test_empty_rows_empty_items():
    assert build_discussion_items([]) == []
