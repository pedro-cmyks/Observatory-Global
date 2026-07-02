"""Shared helper utilities imported by all router modules."""
from urllib.parse import urlparse

_GEO_NAME_BLOCKLIST: set[str] = {
    "abu dhabi", "saudi arabia", "north korea", "south korea", "north africa",
    "south africa", "north america", "south america", "latin america",
    "united states", "united kingdom", "united nations", "united arab emirates",
    "new york", "new delhi", "new zealand", "new jersey", "new mexico",
    "hong kong", "puerto rico", "costa rica", "ivory coast", "sierra leone",
    "burkina faso", "guinea bissau", "equatorial guinea", "papua new guinea",
    "el salvador", "sri lanka", "west bank", "west africa", "east africa",
    "middle east", "central asia", "southeast asia", "south asia",
    "european union", "african union", "las vegas", "los angeles", "san francisco",
    "san jose", "san diego", "rio de janeiro", "sao paulo", "buenos aires",
    "kuala lumpur", "tel aviv", "cape town", "addis ababa", "dar es salaam",
}
_GEO_FIRST_WORDS: set[str] = {"north", "south", "east", "west", "central", "greater", "upper", "lower"}

# #176: non-English non-person phrases the English-only checks above missed —
# multilingual geo forms, climate patterns, and sports-team names that the NER
# tagged as PERSON. Lowercased; matched against the whole name.
_NON_PERSON_PHRASES: set[str] = {
    # climate / nature patterns
    "el niño", "la niña", "el nino", "la nina",
    # sports teams / chants
    "bafana bafana",
    # multilingual geo (Spanish/Portuguese order, demonym pairs)
    "america latina", "latina america", "estados unidos", "reino unido",
    "naciones unidas", "union europea", "unión europea", "oriente medio",
    "medio oriente", "corea del norte", "corea del sur", "arabia saudita",
    "emiratos arabes", "casa blanca", "estado islamico", "estado islámico",
    "nueva york", "nueva delhi", "ciudad de mexico", "ciudad de méxico",
    "reino saudita", "sudafrica", "sudáfrica",
}

# Leading tokens that no real person name starts with (articles, a verb, the
# Spanish/English determiners). Kept deliberately tight: "al" is excluded
# (Al Pacino) and "le"/"o"/"a" are excluded (Le Pen, Portuguese names), so the
# rule never drops a genuine person.
_LEADING_NON_NAME_TOKENS: set[str] = {
    "el", "la", "los", "las", "lo", "un", "una", "unos", "unas", "the", "dar",
}

# Photo-agency / stock-photo credit tokens GDELT extracts from article boilerplate
# ("jonathan borba unsplash", "benvenuti lapresse sipa" — live /country/IT leak,
# 2026-07-01). Token-level match; deliberately EXCLUDES ambiguous real surnames
# ("getty" — J. Paul Getty) and press initialisms ("afp", "epa").
_PHOTO_CREDIT_TOKENS: set[str] = {
    "unsplash", "shutterstock", "istock", "istockphoto", "pexels", "pixabay",
    "lapresse", "sipa", "zuma", "dreamstime", "depositphotos",
}

# Byline scrape class (#248): GDELT glues the "By " credit onto the name →
# "bysarah falson" (44 signals, live). Rule: first token = "by" + a common
# given name of >=4 letters. The length floor protects REAL "by…" names —
# Byron (ron, 3) Buxton/Donalds and Byungjae (ungjae, not a name) survive.
_BYLINE_GIVEN_NAMES: set[str] = {
    "sarah", "kristie", "catherine", "john", "james", "mary", "jane", "david",
    "michael", "peter", "laura", "anna", "emma", "lucy", "mark", "paul",
    "susan", "karen", "linda", "nancy", "lisa", "emily", "rachel", "hannah",
    "george", "thomas", "daniel", "matthew", "andrew", "joshua", "ryan",
    "jessica", "amanda", "melissa", "stephanie", "rebecca", "michelle",
    "jennifer", "elizabeth", "william", "richard", "joseph", "charles",
    "christopher", "anthony", "steven", "kevin", "brian", "jason", "chris",
}


def _is_byline_scrape(first_token: str) -> bool:
    if not first_token.startswith("by") or len(first_token) < 6:
        return False
    return first_token[2:] in _BYLINE_GIVEN_NAMES


# Tech products/protocols GDELT tags as "persons" ("nvidia gpus" served with a
# PERSON badge — capture-doc G1). Token-level; deliberately excludes words that
# occur in real names ("ai" — Ai Weiwei; "meta" — surnames).
_TECH_NON_PERSON_TOKENS: set[str] = {
    "gpu", "gpus", "chatgpt", "iphone", "ipad", "android", "bitcoin",
    "ethereum", "blockchain", "crypto", "wifi", "nvidia", "openai",
    "playstation", "xbox", "tiktok", "whatsapp", "instagram",
}


def _is_valid_person(name: str) -> bool:
    lower = name.lower()
    tokens = lower.split()
    return (
        len(name.split()) >= 2
        and len(name) <= 60
        and lower not in _GEO_NAME_BLOCKLIST
        and lower not in _NON_PERSON_PHRASES
        and tokens[0] not in _GEO_FIRST_WORDS
        and tokens[0] not in _LEADING_NON_NAME_TOKENS
        # byline scrape glued to the name ("bysarah falson")
        and not _is_byline_scrape(tokens[0])
        # photo credits scraped as "people" ("peter hansen unsplash")
        and not any(t in _PHOTO_CREDIT_TOKENS for t in tokens)
        # tech products tagged as people ("nvidia gpus")
        and not any(t in _TECH_NON_PERSON_TOKENS for t in tokens)
        # a real two-word name never repeats the exact same token
        # ("bafana bafana", "new new")
        and len(set(tokens)) > 1
    )


def rank_key_people(rows, *, limit: int = 8, min_headlines: int = 2) -> list:
    """Rank person mentions resistant to syndication (#176).

    Raw COUNT(*) lets one wire-service story republished by many outlets (a
    syndicated obituary) outrank locally-reported actors — the David-Hockney-
    leads-Peru bug. Rank instead by how many DISTINCT stories/outlets a person
    appears in, and drop anyone below a corroboration floor of ``min_headlines``
    distinct headlines so a single mass-republished story can't lead the panel.
    Falls back to the unfiltered ranking when nobody clears the floor, so a
    low-coverage country still gets a People panel rather than a blank one.

    ``rows`` are plain dicts (convert asyncpg Records with ``dict(r)``) carrying
    at least ``person``; ``distinct_headlines``/``distinct_outlets``/
    ``signal_count`` default to 1/1/0 when absent (backward-compatible)."""
    def _hl(r):
        return int(r.get("distinct_headlines") or 1)

    def _sort_key(r):
        return (_hl(r), int(r.get("distinct_outlets") or 1), int(r.get("signal_count") or 0))

    valid = [r for r in rows if _is_valid_person(r.get("person", ""))]
    corroborated = [r for r in valid if _hl(r) >= min_headlines]
    pool = corroborated or valid  # fallback: never blank a populated panel
    return sorted(pool, key=_sort_key, reverse=True)[:limit]


def _resolve_persons(nlp_persons, gdelt_persons) -> list:
    """Prefer NLP-extracted persons (PERSON type only); fall back to GDELT."""
    if nlp_persons:
        import json as _json
        data = _json.loads(nlp_persons) if isinstance(nlp_persons, str) else nlp_persons
        names = [e["name"] for e in data if e.get("type") == "PERSON"]
        if names:
            return names[:3]
    return (gdelt_persons or [])[:3]


def extract_domain(source_url: str) -> str:
    if not source_url:
        return "Unknown"
    try:
        parsed = urlparse(source_url if source_url.startswith('http') else f'http://{source_url}')
        domain = parsed.netloc or parsed.path
        return domain.replace('www.', '').split('/')[0] or source_url[:30]
    except (ValueError, AttributeError):
        return source_url[:30]
