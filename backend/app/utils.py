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


def _is_valid_person(name: str) -> bool:
    lower = name.lower()
    return (
        len(name.split()) >= 2
        and len(name) <= 60
        and lower not in _GEO_NAME_BLOCKLIST
        and lower.split()[0] not in _GEO_FIRST_WORDS
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
