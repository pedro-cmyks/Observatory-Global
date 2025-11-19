"""
GDELT Theme Taxonomy Mapping

This module provides the mapping between GDELT's 280+ raw theme codes
and human-readable labels for UI display.

Based on GDELT_SCHEMA_ANALYSIS.md lines 240-287 and real GDELT GKG taxonomy.

Top 50 most common themes (covers ~85% of real GDELT data)
"""

from typing import Dict, List

# ===== TOP 50 MOST COMMON GDELT THEMES =====
# Each theme is a dict with: code, label, category, description, aliases

THEME_TAXONOMY: Dict[str, dict] = {
    # ===== SECURITY & CONFLICT =====
    "TAX_TERROR": {
        "code": "TAX_TERROR",
        "label": "Terrorism",
        "category": "security",
        "description": "Terrorist activities, extremism, and related security threats",
        "aliases": ["terror", "terrorism", "extremism", "terrorist attacks"]
    },
    "ARMEDCONFLICT": {
        "code": "ARMEDCONFLICT",
        "label": "Armed Conflict",
        "category": "security",
        "description": "Military conflicts, warfare, armed clashes",
        "aliases": ["war", "conflict", "military", "warfare", "combat"]
    },
    "CRISISLEX_C03_DEAD_WOUNDED": {
        "code": "CRISISLEX_C03_DEAD_WOUNDED",
        "label": "Casualties",
        "category": "security",
        "description": "Deaths and injuries from conflicts or disasters",
        "aliases": ["casualties", "deaths", "wounded", "fatalities", "injuries"]
    },
    "CRISISLEX_C06_VIOLENCE": {
        "code": "CRISISLEX_C06_VIOLENCE",
        "label": "Violence",
        "category": "security",
        "description": "Acts of violence, attacks, and violent incidents",
        "aliases": ["violence", "attacks", "violent incidents"]
    },
    "CRIME": {
        "code": "CRIME",
        "label": "Crime & Law Enforcement",
        "category": "security",
        "description": "Criminal activities and law enforcement responses",
        "aliases": ["crime", "criminal", "law enforcement", "police"]
    },
    "ARREST": {
        "code": "ARREST",
        "label": "Arrests",
        "category": "security",
        "description": "Law enforcement arrests and detentions",
        "aliases": ["arrest", "detention", "custody"]
    },
    "KILL": {
        "code": "KILL",
        "label": "Killings",
        "category": "security",
        "description": "Killings and homicides",
        "aliases": ["killing", "murder", "homicide", "death"]
    },
    "MILITARY": {
        "code": "MILITARY",
        "label": "Military Affairs",
        "category": "security",
        "description": "Military operations, defense policy, armed forces",
        "aliases": ["military", "defense", "armed forces", "troops", "army"]
    },
    "SEIZE": {
        "code": "SEIZE",
        "label": "Seizures & Confiscations",
        "category": "security",
        "description": "Asset seizures, confiscations, takeovers",
        "aliases": ["seize", "confiscate", "takeover", "seizure"]
    },
    "CYBERATTACK": {
        "code": "CYBERATTACK",
        "label": "Cyber Attacks",
        "category": "security",
        "description": "Cyber attacks, hacking, data breaches",
        "aliases": ["cyberattack", "hacking", "data breach", "cyber security"]
    },

    # ===== ECONOMICS & FINANCE =====
    "TAX_FNCACT": {
        "code": "TAX_FNCACT",
        "label": "Financial Activity",
        "category": "economy",
        "description": "Financial markets, banking, and economic activities",
        "aliases": ["finance", "financial", "banking", "markets", "economy"]
    },
    "ECON_INFLATION": {
        "code": "ECON_INFLATION",
        "label": "Inflation",
        "category": "economy",
        "description": "Inflation rates, price increases, cost of living",
        "aliases": ["inflation", "prices", "cost of living", "price increases"]
    },
    "ECON_TRADE": {
        "code": "ECON_TRADE",
        "label": "International Trade",
        "category": "economy",
        "description": "Trade agreements, exports, imports, tariffs",
        "aliases": ["trade", "exports", "imports", "tariffs", "trade deals"]
    },
    "ECON_BANKRUPTCY": {
        "code": "ECON_BANKRUPTCY",
        "label": "Bankruptcy",
        "category": "economy",
        "description": "Business failures, bankruptcies, financial distress",
        "aliases": ["bankruptcy", "insolvency", "business failure"]
    },
    "WB_633_ECONOMIC_STABILITY": {
        "code": "WB_633_ECONOMIC_STABILITY",
        "label": "Economic Stability",
        "category": "economy",
        "description": "Economic stability, growth, and macroeconomic indicators",
        "aliases": ["economic stability", "growth", "gdp", "economic health"]
    },
    "AGRICULTURE": {
        "code": "AGRICULTURE",
        "label": "Agriculture",
        "category": "economy",
        "description": "Agriculture, farming, food production",
        "aliases": ["agriculture", "farming", "crops", "food production", "rural"]
    },
    "ENERGY": {
        "code": "ENERGY",
        "label": "Energy",
        "category": "economy",
        "description": "Energy policy, oil, gas, renewable energy",
        "aliases": ["energy", "oil", "gas", "renewables", "power"]
    },
    "LABOR": {
        "code": "LABOR",
        "label": "Labor & Employment",
        "category": "economy",
        "description": "Labor issues, employment, workers' rights",
        "aliases": ["labor", "employment", "workers", "jobs", "unemployment"]
    },
    "STRIKE": {
        "code": "STRIKE",
        "label": "Strikes",
        "category": "economy",
        "description": "Labor strikes, industrial action",
        "aliases": ["strike", "walkout", "industrial action", "labor protest"]
    },

    # ===== POLITICS & GOVERNANCE =====
    "LEADER": {
        "code": "LEADER",
        "label": "Political Leadership",
        "category": "politics",
        "description": "Political leaders, heads of state, government officials",
        "aliases": ["leaders", "politicians", "government", "officials"]
    },
    "ELECTION": {
        "code": "ELECTION",
        "label": "Elections",
        "category": "politics",
        "description": "Elections, voting, electoral processes",
        "aliases": ["election", "voting", "ballot", "electoral", "polls"]
    },
    "GOVERNMENT": {
        "code": "GOVERNMENT",
        "label": "Government Actions",
        "category": "politics",
        "description": "Government policies, decisions, and actions",
        "aliases": ["government", "policy", "legislation", "law"]
    },
    "PROTEST": {
        "code": "PROTEST",
        "label": "Protests & Demonstrations",
        "category": "politics",
        "description": "Public protests, demonstrations, civil unrest",
        "aliases": ["protest", "demonstration", "rally", "civil unrest", "activism"]
    },
    "CORRUPTION": {
        "code": "CORRUPTION",
        "label": "Corruption",
        "category": "politics",
        "description": "Political corruption, bribery, fraud",
        "aliases": ["corruption", "bribery", "fraud", "graft", "embezzlement"]
    },
    "TAX_DIPLOMACY": {
        "code": "TAX_DIPLOMACY",
        "label": "Diplomacy",
        "category": "politics",
        "description": "Diplomatic relations, negotiations, international cooperation",
        "aliases": ["diplomacy", "diplomatic", "negotiations", "foreign relations"]
    },
    "WB_632_WOMEN_IN_POLITICS": {
        "code": "WB_632_WOMEN_IN_POLITICS",
        "label": "Women in Politics",
        "category": "politics",
        "description": "Female political participation and leadership",
        "aliases": ["women in politics", "female leaders", "gender equality politics"]
    },
    "SANCTION": {
        "code": "SANCTION",
        "label": "Sanctions",
        "category": "politics",
        "description": "Economic sanctions, embargoes, trade restrictions",
        "aliases": ["sanctions", "embargo", "restrictions", "penalties"]
    },
    "TREATY": {
        "code": "TREATY",
        "label": "Treaties & Agreements",
        "category": "politics",
        "description": "International treaties, agreements, pacts",
        "aliases": ["treaty", "agreement", "pact", "accord", "deal"]
    },
    "COURT": {
        "code": "COURT",
        "label": "Legal Proceedings",
        "category": "politics",
        "description": "Court cases, legal proceedings, judiciary",
        "aliases": ["court", "legal", "judge", "trial", "lawsuit"]
    },
    "INVESTIGATION": {
        "code": "INVESTIGATION",
        "label": "Investigations",
        "category": "politics",
        "description": "Official investigations, inquiries, probes",
        "aliases": ["investigation", "inquiry", "probe", "review"]
    },

    # ===== ENVIRONMENT & CLIMATE =====
    "ENV_CLIMATECHANGE": {
        "code": "ENV_CLIMATECHANGE",
        "label": "Climate Change",
        "category": "environment",
        "description": "Climate change, global warming, environmental policy",
        "aliases": ["climate change", "global warming", "climate crisis", "climate policy"]
    },
    "ENV_FORESTS": {
        "code": "ENV_FORESTS",
        "label": "Deforestation & Forests",
        "category": "environment",
        "description": "Forests, deforestation, conservation",
        "aliases": ["forests", "deforestation", "rainforest", "conservation"]
    },
    "ENV_POLLUTION": {
        "code": "ENV_POLLUTION",
        "label": "Pollution",
        "category": "environment",
        "description": "Environmental pollution, air quality, water contamination",
        "aliases": ["pollution", "air quality", "contamination", "emissions"]
    },
    "UNGP_DISASTER": {
        "code": "UNGP_DISASTER",
        "label": "Natural Disasters",
        "category": "environment",
        "description": "Natural disasters, earthquakes, floods, hurricanes",
        "aliases": ["disaster", "earthquake", "flood", "hurricane", "natural disaster"]
    },
    "DISASTER_RESPONSE": {
        "code": "DISASTER_RESPONSE",
        "label": "Disaster Response",
        "category": "environment",
        "description": "Emergency response, disaster relief, humanitarian aid",
        "aliases": ["disaster response", "relief", "emergency", "humanitarian aid"]
    },

    # ===== HEALTH & SOCIAL =====
    "HEALTH": {
        "code": "HEALTH",
        "label": "Public Health",
        "category": "health",
        "description": "Public health issues, healthcare, disease outbreaks",
        "aliases": ["health", "healthcare", "medical", "disease", "pandemic"]
    },
    "EDUCATION": {
        "code": "EDUCATION",
        "label": "Education",
        "category": "social",
        "description": "Education policy, schools, universities",
        "aliases": ["education", "schools", "university", "students", "learning"]
    },
    "HUMAN_RIGHTS": {
        "code": "HUMAN_RIGHTS",
        "label": "Human Rights",
        "category": "social",
        "description": "Human rights issues, civil liberties, freedoms",
        "aliases": ["human rights", "civil liberties", "freedoms", "rights"]
    },
    "MIGRATION": {
        "code": "MIGRATION",
        "label": "Migration & Refugees",
        "category": "social",
        "description": "Migration, refugees, asylum, immigration",
        "aliases": ["migration", "refugees", "asylum", "immigration", "migrants"]
    },
    "RELIGION": {
        "code": "RELIGION",
        "label": "Religion",
        "category": "social",
        "description": "Religious topics, interfaith relations, religious freedom",
        "aliases": ["religion", "religious", "faith", "church", "mosque", "temple"]
    },
    "SOC_POINTSOFVIEW": {
        "code": "SOC_POINTSOFVIEW",
        "label": "Social Perspectives",
        "category": "social",
        "description": "Social commentary, opinions, perspectives",
        "aliases": ["opinions", "perspectives", "views", "commentary", "discourse"]
    },

    # ===== MEDIA & TECHNOLOGY =====
    "MEDIA_MSM": {
        "code": "MEDIA_MSM",
        "label": "Mainstream Media",
        "category": "media",
        "description": "Mainstream media coverage, journalism, news",
        "aliases": ["media", "news", "journalism", "press", "msm"]
    },
    "TECHNOLOGY": {
        "code": "TECHNOLOGY",
        "label": "Technology",
        "category": "technology",
        "description": "Technology developments, innovation, digital transformation",
        "aliases": ["technology", "tech", "digital", "innovation", "ai", "software"]
    },
    "SPACE": {
        "code": "SPACE",
        "label": "Space Exploration",
        "category": "technology",
        "description": "Space exploration, satellites, aerospace",
        "aliases": ["space", "satellite", "aerospace", "nasa", "rocket"]
    },

    # ===== INFRASTRUCTURE & CULTURE =====
    "TRANSPORT": {
        "code": "TRANSPORT",
        "label": "Transportation",
        "category": "infrastructure",
        "description": "Transportation, infrastructure, logistics",
        "aliases": ["transport", "transportation", "infrastructure", "roads", "railways"]
    },
    "SPORTS": {
        "code": "SPORTS",
        "label": "Sports",
        "category": "culture",
        "description": "Sports events, competitions, athletes",
        "aliases": ["sports", "athletics", "competition", "games", "tournament"]
    },
    "ENTERTAINMENT": {
        "code": "ENTERTAINMENT",
        "label": "Entertainment",
        "category": "culture",
        "description": "Entertainment industry, celebrities, arts",
        "aliases": ["entertainment", "celebrity", "arts", "culture", "music"]
    },
}


# ===== CATEGORY GROUPINGS =====

THEME_CATEGORIES = {
    "security": [
        "TAX_TERROR", "ARMEDCONFLICT", "CRISISLEX_C03_DEAD_WOUNDED",
        "CRISISLEX_C06_VIOLENCE", "CRIME", "ARREST", "KILL",
        "MILITARY", "SEIZE", "CYBERATTACK"
    ],
    "economy": [
        "TAX_FNCACT", "ECON_INFLATION", "ECON_TRADE", "ECON_BANKRUPTCY",
        "WB_633_ECONOMIC_STABILITY", "AGRICULTURE", "ENERGY", "LABOR", "STRIKE"
    ],
    "politics": [
        "LEADER", "ELECTION", "GOVERNMENT", "PROTEST", "CORRUPTION",
        "TAX_DIPLOMACY", "WB_632_WOMEN_IN_POLITICS", "SANCTION",
        "TREATY", "COURT", "INVESTIGATION"
    ],
    "environment": [
        "ENV_CLIMATECHANGE", "ENV_FORESTS", "ENV_POLLUTION",
        "UNGP_DISASTER", "DISASTER_RESPONSE"
    ],
    "health": ["HEALTH"],
    "social": [
        "EDUCATION", "HUMAN_RIGHTS", "MIGRATION", "RELIGION",
        "SOC_POINTSOFVIEW"
    ],
    "media": ["MEDIA_MSM"],
    "technology": ["TECHNOLOGY", "SPACE"],
    "infrastructure": ["TRANSPORT"],
    "culture": ["SPORTS", "ENTERTAINMENT"],
}


# ===== UTILITY FUNCTIONS =====

def get_theme_label(theme_code: str) -> str:
    """Get human-readable label for a GDELT theme code."""
    if theme_code in THEME_TAXONOMY:
        return THEME_TAXONOMY[theme_code]["label"]
    # Fallback: Format unknown codes
    return theme_code.replace("_", " ").title()


def get_theme_category(theme_code: str) -> str:
    """Get category for a GDELT theme code."""
    if theme_code in THEME_TAXONOMY:
        return THEME_TAXONOMY[theme_code]["category"]
    return "other"


def get_themes_by_category(category: str) -> List[str]:
    """Get all theme codes for a given category."""
    return THEME_CATEGORIES.get(category, [])


def search_themes(query: str, limit: int = 10) -> List[dict]:
    """Search themes by label, code, or alias."""
    query_lower = query.lower()
    matches = []

    for theme_code, theme in THEME_TAXONOMY.items():
        # Exact code match (highest priority)
        if theme_code.lower() == query_lower:
            matches.insert(0, theme)
            continue

        # Label match
        if query_lower in theme["label"].lower():
            matches.append(theme)
            continue

        # Alias match
        if any(query_lower in alias.lower() for alias in theme["aliases"]):
            matches.append(theme)
            continue

    return matches[:limit]


def get_all_theme_codes() -> List[str]:
    """Get list of all available theme codes."""
    return list(THEME_TAXONOMY.keys())


def get_all_categories() -> List[str]:
    """Get list of all categories."""
    return list(THEME_CATEGORIES.keys())


__all__ = [
    "THEME_TAXONOMY",
    "THEME_CATEGORIES",
    "get_theme_label",
    "get_theme_category",
    "get_themes_by_category",
    "search_themes",
    "get_all_theme_codes",
    "get_all_categories",
]
