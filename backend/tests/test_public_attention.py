"""Forum public-attention lane (L2 C1/C3)."""
from app.services.public_attention import parse_dynamic_topic_id, subreddit_label


def test_parse_dynamic_topic_id():
    assert parse_dynamic_topic_id("dynamic-topic-12") == 12
    assert parse_dynamic_topic_id("dynamic-topic-007") == 7
    assert parse_dynamic_topic_id("42") == 42
    assert parse_dynamic_topic_id(None) is None
    assert parse_dynamic_topic_id("") is None
    # Non-dynamic threads have no centroid → no per-thread forum match.
    assert parse_dynamic_topic_id("armed-conflict--co") is None
    assert parse_dynamic_topic_id("emergent-cluster-9") is None
    assert parse_dynamic_topic_id("query-thread::iran water 5") is None


def test_subreddit_label_strips_reddit_prefix():
    assert subreddit_label("reddit/r/colombia") == "r/colombia"
    assert subreddit_label("reddit/r/SyrianCivilWar") == "r/SyrianCivilWar"


def test_subreddit_label_passthrough_and_none():
    assert subreddit_label("mastodon/social") == "mastodon/social"
    assert subreddit_label(None) is None
    assert subreddit_label("") is None
