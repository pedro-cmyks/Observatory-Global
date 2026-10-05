"""The snapshot path rule must match frontend-v2/src/lib/staticEdition.ts.
Same examples as staticEdition.test.ts — change both."""
from scripts.build_static_edition import edition_path, pick_countries

EXAMPLES = [
    ("/api/v2/briefing?hours=24", "edition/api/v2/briefing__hours=24.json"),
    ("/api/v2/country-edition?hours=24&cc=CO", "edition/api/v2/country-edition__cc=CO&hours=24.json"),
    ("/api/v2/country-edition?cc=CO&hours=24", "edition/api/v2/country-edition__cc=CO&hours=24.json"),
    ("/api/v2/nodes?focus_type=country&focus_value=US&hours=24&limit=5",
     "edition/api/v2/nodes__focus_type=country&focus_value=US&hours=24&limit=5.json"),
    ("/api/v2/delight", "edition/api/v2/delight.json"),
    ("/api/v2/investigation/daily-publication", "edition/api/v2/investigation/daily-publication.json"),
    ("/api/v2/search/unified?q=hello%20world&hours=24", "edition/api/v2/search/unified__hours=24&q=hello-world.json"),
    ("/health", "edition/health.json"),
]


def test_path_rule_matches_the_frontend():
    for url, want in EXAMPLES:
        assert edition_path(url) == want, url


def test_pick_countries_dedups_uppercases_and_caps():
    heat = {"items": [{"country_code": "us"}, {"country_code": "CO"}, {"country_code": "us"}, {"code": "x"}]}
    briefing = {"heat_countries": [{"country_code": "IR"}], "top_threads": [{"countries": ["CO", "RU"]}]}
    assert pick_countries(heat, briefing, cap=10) == ["US", "CO", "IR", "RU"]
    assert pick_countries(heat, briefing, cap=2) == ["US", "CO"]
