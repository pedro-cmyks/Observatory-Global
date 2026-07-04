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


def test_forum_noise_lane_hobby_community():
    """#248: hobby communities damp regardless of headline."""
    from app.services.public_attention import _forum_noise_lane

    assert _forum_noise_lane("crochet@lemmy.ca", "Little wolf girl I made my daughter") == "hobby"
    assert _forum_noise_lane("aviation@lemmy.ca", "Helicopters at the World Cup") == "hobby"
    assert _forum_noise_lane("gaming@beehaw.org", "What are you playing this week?") == "hobby"


def test_forum_noise_lane_news_untouched():
    """Real news discussion never gets a noise lane."""
    from app.services.public_attention import _forum_noise_lane

    assert _forum_noise_lane("worldnews@lemmy.world", "Israel and Lebanon reach draft agreement") is None
    assert _forum_noise_lane("politics@lemmy.world", "Judge blocks mail-in ballot order") is None
    assert _forum_noise_lane("ukraine@sopuli.xyz", "Russian strikes hit Kharkiv overnight") is None


def test_forum_noise_lane_personal_markers():
    """Personal/hobby headline markers catch posts from unlisted communities."""
    from app.services.public_attention import _forum_noise_lane

    assert _forum_noise_lane(None, "My first sourdough finally worked") == "hobby"
    assert _forum_noise_lane("randomcommunity@x.tld", "I made a lamp from driftwood") == "hobby"
