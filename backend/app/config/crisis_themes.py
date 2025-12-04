"""
Crisis theme configuration for Observatory Crisis Watch.
Defines which GDELT themes are relevant for crisis monitoring.
"""
from typing import List, Dict, Optional

# Primary crisis-related theme codes from GDELT taxonomy
CRISIS_THEME_PREFIXES = [
    # CrisisLex taxonomy (disaster/emergency specific)
    "CRISISLEX",
    
    # Violence and conflict
    "KILL", "WOUND", "ARREST", "KIDNAP",
    "TERROR", "MILITARY", "REBELLION", "INSURGENCY",
    "WAR", "CONFLICT", "VIOLENCE", "MASSACRE",
    "PROTEST", "RIOT", "DEMONSTRATION",
    "SEIZE", "BLOCKADE",
    
    # Political instability
    "COUP", "IMPEACH", "ASSASSINATION",
    "POLITICAL_TURMOIL", "GOVT_COLLAPSE",
    "ELECTION_FRAUD", "MARTIAL_LAW",
    
    # Natural disasters
    "NATURAL_DISASTER", "EARTHQUAKE", "FLOOD",
    "HURRICANE", "TYPHOON", "CYCLONE",
    "WILDFIRE", "DROUGHT", "TSUNAMI",
    "VOLCANO", "AVALANCHE", "LANDSLIDE",
    "TORNADO", "STORM",
    
    # Humanitarian crises
    "REFUGEE", "FAMINE", "HUMANITARIAN",
    "EPIDEMIC", "PANDEMIC", "DISEASE_OUTBREAK",
    "DISPLACEMENT",
    
    # Security threats
    "CYBER_ATTACK", "HOSTAGE", "BOMBING",
    "SHOOTING", "ATTACK", "EXPLOSIVE",
]

# Human-readable labels for UI display
CRISIS_THEME_LABELS: Dict[str, str] = {
    # CrisisLex
    "CRISISLEX_CRISISLEXREC": "Crisis Event",
    "CRISISLEX_C01_CASUALTIES": "Casualties Reported",
    "CRISISLEX_C02_SAFETY": "Safety Concerns",
    "CRISISLEX_C03_SHELTER": "Shelter Needs",
    "CRISISLEX_C04_FOOD_WATER": "Food/Water Shortage",
    "CRISISLEX_C05_MEDICAL": "Medical Emergency",
    "CRISISLEX_C06_INFRASTRUCTURE": "Infrastructure Damage",
    "CRISISLEX_C07_SEARCH_RESCUE": "Search & Rescue",
    "CRISISLEX_C08_LOGISTICS": "Logistics Issues",
    "CRISISLEX_C09_DONATIONS": "Aid & Donations",
    "CRISISLEX_C10_EVACUATION": "Evacuation",
    
    # Violence
    "KILL": "Fatalities",
    "WOUND": "Injuries",
    "ARREST": "Arrests",
    "KIDNAP": "Kidnapping",
    "PROTEST": "Protests",
    "RIOT": "Riots",
    "TERROR": "Terrorism",
    "MILITARY": "Military Action",
    "WAR": "Armed Conflict",
    "CONFLICT": "Conflict",
    "MASSACRE": "Mass Casualties",
    
    # Political
    "COUP": "Coup Attempt",
    "IMPEACH": "Impeachment",
    "ASSASSINATION": "Assassination",
    
    # Natural disasters
    "EARTHQUAKE": "Earthquake",
    "FLOOD": "Flooding",
    "HURRICANE": "Hurricane",
    "TYPHOON": "Typhoon",
    "WILDFIRE": "Wildfire",
    "TSUNAMI": "Tsunami",
    "VOLCANO": "Volcanic Activity",
    "DROUGHT": "Drought",
    "TORNADO": "Tornado",
    
    # Humanitarian
    "REFUGEE": "Refugee Crisis",
    "FAMINE": "Famine",
    "EPIDEMIC": "Disease Outbreak",
    "PANDEMIC": "Pandemic",
}

# Crisis severity mapping (for prioritization)
SEVERITY_KEYWORDS: Dict[str, List[str]] = {
    "critical": ["WAR", "MASSACRE", "GENOCIDE", "FAMINE", "PANDEMIC", "TSUNAMI", "ASSASSINATION"],
    "high": ["TERROR", "COUP", "EARTHQUAKE", "KILL", "HURRICANE", "TYPHOON", "HOSTAGE"],
    "medium": ["PROTEST", "RIOT", "FLOOD", "WILDFIRE", "CONFLICT", "MILITARY", "EPIDEMIC"],
    "low": ["DEMONSTRATION", "ARREST", "DROUGHT", "STORM"],
}

# Event type mapping
EVENT_TYPE_KEYWORDS: Dict[str, List[str]] = {
    "armed_conflict": ["WAR", "MILITARY", "CONFLICT", "REBELLION", "INSURGENCY"],
    "civil_unrest": ["PROTEST", "RIOT", "DEMONSTRATION", "STRIKE"],
    "terrorism": ["TERROR", "BOMBING", "ATTACK", "HOSTAGE"],
    "natural_disaster": ["EARTHQUAKE", "FLOOD", "HURRICANE", "TYPHOON", "WILDFIRE", "TSUNAMI", "VOLCANO", "TORNADO", "DROUGHT"],
    "political_crisis": ["COUP", "IMPEACH", "ASSASSINATION", "ELECTION_FRAUD"],
    "humanitarian": ["REFUGEE", "FAMINE", "DISPLACEMENT", "HUMANITARIAN"],
    "health_emergency": ["EPIDEMIC", "PANDEMIC", "DISEASE_OUTBREAK"],
    "violence": ["KILL", "WOUND", "MASSACRE", "SHOOTING"],
}


def is_crisis_theme(theme_code: str) -> bool:
    """Check if a theme code is crisis-related."""
    if not theme_code:
        return False
    theme_upper = theme_code.upper()
    return any(prefix in theme_upper for prefix in CRISIS_THEME_PREFIXES)


def get_crisis_themes(themes: List[str]) -> List[str]:
    """Filter a list of themes to only crisis-related ones."""
    if not themes:
        return []
    return [t for t in themes if is_crisis_theme(t)]


def get_crisis_label(theme_code: str) -> str:
    """Get human-readable label for a crisis theme."""
    if not theme_code:
        return "Unknown"
    
    theme_upper = theme_code.upper()
    
    # Check exact match first
    if theme_upper in CRISIS_THEME_LABELS:
        return CRISIS_THEME_LABELS[theme_upper]
    
    # Check prefix match
    for prefix, label in CRISIS_THEME_LABELS.items():
        if prefix in theme_upper:
            return label
    
    # Fallback: clean up the code
    clean = theme_code.replace("_", " ").replace("CRISISLEX", "").strip()
    return clean.title() if clean else theme_code


def calculate_severity(themes: List[str]) -> str:
    """Calculate crisis severity based on themes present."""
    if not themes:
        return "low"
    
    themes_upper = " ".join(themes).upper()
    
    for severity, keywords in SEVERITY_KEYWORDS.items():
        if any(kw in themes_upper for kw in keywords):
            return severity
    
    return "low"


def get_event_type(themes: List[str]) -> str:
    """Categorize event into broad types based on themes."""
    if not themes:
        return "other"
    
    themes_upper = " ".join(themes).upper()
    
    for event_type, keywords in EVENT_TYPE_KEYWORDS.items():
        if any(kw in themes_upper for kw in keywords):
            return event_type
    
    return "other"


def calculate_crisis_score(themes: List[str]) -> float:
    """
    Calculate a 0-1 crisis relevance score.
    Higher = more crisis-related content.
    """
    if not themes:
        return 0.0
    
    crisis_themes = get_crisis_themes(themes)
    if not crisis_themes:
        return 0.0
    
    base_score = len(crisis_themes) / len(themes)
    
    # Boost for high-severity themes
    severity = calculate_severity(crisis_themes)
    severity_boost = {
        "critical": 0.3,
        "high": 0.2,
        "medium": 0.1,
        "low": 0.0
    }
    
    return min(1.0, base_score + severity_boost.get(severity, 0))
