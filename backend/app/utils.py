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
        # a real two-word name never repeats the exact same token
        # ("bafana bafana", "new new")
        and len(set(tokens)) > 1
    )


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
