"""Forum public-attention lane (L2 C1)."""
from app.services.public_attention import subreddit_label


def test_subreddit_label_strips_reddit_prefix():
    assert subreddit_label("reddit/r/colombia") == "r/colombia"
    assert subreddit_label("reddit/r/SyrianCivilWar") == "r/SyrianCivilWar"


def test_subreddit_label_passthrough_and_none():
    assert subreddit_label("mastodon/social") == "mastodon/social"
    assert subreddit_label(None) is None
    assert subreddit_label("") is None
