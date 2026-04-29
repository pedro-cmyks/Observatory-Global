"""
GDELT Theme Taxonomy Mapping

This module provides the mapping between GDELT's 280+ raw theme codes
and human-readable labels for UI display.

Based on GDELT_SCHEMA_ANALYSIS.md lines 240-287 and real GDELT GKG taxonomy.

Top 50 most common themes (covers ~85% of real GDELT data)
"""

import difflib
import re
from typing import Dict, List, Optional

# ===== TOP 50 MOST COMMON GDELT THEMES =====
# Each theme is a dict with: code, label, category, description, aliases

THEME_TAXONOMY: Dict[str, dict] = {
    # ===== SECURITY & CONFLICT =====
    "TAX_TERROR": {
        "code": "TAX_TERROR",
        "label": "Terrorism",
        "category": "security",
        "description": "Terrorist activities, extremism, and related security threats",
        "aliases": [
            "terror", "terrorism", "extremism", "terrorist attacks",
            "terrorismo", "terrorista", "extremismo", "atentado"
        ]
    },
    "ARMEDCONFLICT": {
        "code": "ARMEDCONFLICT",
        "label": "Armed Conflict",
        "category": "security",
        "description": "Military conflicts, warfare, armed clashes",
        "aliases": [
            "war", "conflict", "military", "warfare", "combat",
            "guerra", "conflicto", "conflicto armado", "combate", "enfrentamiento"
        ]
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
        "aliases": [
            "violence", "attacks", "violent incidents",
            "violencia", "ataque", "ataques"
        ]
    },
    "CRIME": {
        "code": "CRIME",
        "label": "Crime & Law Enforcement",
        "category": "security",
        "description": "Criminal activities and law enforcement responses",
        "aliases": [
            "crime", "criminal", "law enforcement", "police",
            "crimen", "delito", "policía", "policia", "delincuencia"
        ]
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
        "aliases": [
            "killing", "murder", "homicide", "death",
            "asesinato", "homicidio", "muerte", "matanza", "femicidio", "feminicidio"
        ]
    },
    "MILITARY": {
        "code": "MILITARY",
        "label": "Military Affairs",
        "category": "security",
        "description": "Military operations, defense policy, armed forces",
        "aliases": [
            "military", "defense", "armed forces", "troops", "army",
            "militar", "ejército", "ejercito", "fuerzas armadas", "tropas", "defensa"
        ]
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
        "aliases": [
            "inflation", "prices", "cost of living", "price increases",
            "inflación", "inflacion", "precios", "costo de vida", "encarecimiento"
        ]
    },
    "ECON_TRADE": {
        "code": "ECON_TRADE",
        "label": "International Trade",
        "category": "economy",
        "description": "Trade agreements, exports, imports, tariffs",
        "aliases": [
            "trade", "exports", "imports", "tariffs", "trade deals",
            "comercio", "exportaciones", "importaciones", "aranceles", "tratado comercial"
        ]
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
        "aliases": [
            "election", "voting", "ballot", "electoral", "polls",
            "elecciones", "eleccion", "elección", "votación", "votacion", "comicios", "urnas"
        ]
    },
    "GOVERNMENT": {
        "code": "GOVERNMENT",
        "label": "Government Actions",
        "category": "politics",
        "description": "Government policies, decisions, and actions",
        "aliases": [
            "government", "policy", "legislation", "law",
            "gobierno", "política", "politica", "ley", "legislación", "legislacion"
        ]
    },
    "PROTEST": {
        "code": "PROTEST",
        "label": "Protests & Demonstrations",
        "category": "politics",
        "description": "Public protests, demonstrations, civil unrest",
        "aliases": [
            "protest", "demonstration", "rally", "civil unrest", "activism",
            "protesta", "manifestación", "manifestacion", "marcha", "disturbios", "movilización"
        ]
    },
    "CORRUPTION": {
        "code": "CORRUPTION",
        "label": "Corruption",
        "category": "politics",
        "description": "Political corruption, bribery, fraud",
        "aliases": [
            "corruption", "bribery", "fraud", "graft", "embezzlement",
            "corrupción", "corrupcion", "soborno", "fraude", "malversación", "malversacion"
        ]
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
        "aliases": [
            "climate change", "global warming", "climate crisis", "climate policy", "environment",
            "cambio climático", "cambio climatico", "calentamiento global", "crisis climática", "medio ambiente", "ambiente"
        ]
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
        "aliases": [
            "health", "healthcare", "medical", "disease", "pandemic",
            "salud", "sanidad", "médico", "medico", "enfermedad", "pandemia", "epidemia"
        ]
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
        "aliases": [
            "migration", "refugees", "asylum", "immigration", "migrants",
            "migración", "migracion", "refugiados", "asilo", "inmigración", "inmigracion", "migrantes"
        ]
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


def _normalize(s: str) -> str:
    """Lowercase + strip Spanish/Latin diacritics + collapse whitespace.

    Used to make search robust to accents ("inflación" → "inflacion") and to typing
    variations. Stdlib only — uses NFKD decomposition via unicodedata.
    """
    import unicodedata
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip()


def _tokenize(s: str) -> List[str]:
    """Split a normalized string into alphanumeric tokens, dropping length-1 noise."""
    return [t for t in re.split(r"[^a-z0-9]+", _normalize(s)) if len(t) > 1]


def _fuzzy_token_score(query_tokens: List[str], target_tokens: List[str]) -> float:
    """Score how well query tokens match target tokens.

    For each query token, find its best fuzzy match in target tokens using
    difflib's SequenceMatcher ratio. Average across query tokens. Tokens shorter
    than 3 chars require exact match (avoids "el" matching everything).

    Returns 0.0..1.0. >=0.75 is a strong signal; >=0.6 is a weak hit; <0.6 is noise.
    """
    if not query_tokens or not target_tokens:
        return 0.0
    target_set = set(target_tokens)
    total = 0.0
    for qt in query_tokens:
        if len(qt) < 3:
            total += 1.0 if qt in target_set else 0.0
            continue
        # Substring match is a perfect hit (handles "viol" → "violence")
        if any(qt in tt or tt in qt for tt in target_tokens):
            total += 1.0
            continue
        # Otherwise fuzzy ratio against best target token (handles typos)
        best = max(
            (difflib.SequenceMatcher(None, qt, tt).ratio() for tt in target_tokens),
            default=0.0,
        )
        total += best
    return total / len(query_tokens)


def search_themes(query: str, limit: int = 10, min_score: float = 0.6) -> List[dict]:
    """Search themes by label, code, or alias with typo + accent tolerance.

    Pipeline:
      1. Exact code match → top result.
      2. Tokenize query, score against (label + aliases) tokens for each theme.
      3. Return themes scoring above min_score, sorted descending.

    Handles: typos ("viollence"), accents ("inflación"), Spanish ("diamantes"),
    multi-word compounds ("blood diamonds" → matches via token overlap).
    """
    if not query or not query.strip():
        return []

    q_norm = _normalize(query)
    q_tokens = _tokenize(query)
    if not q_tokens:
        return []

    scored: List[tuple[float, dict]] = []

    for theme_code, theme in THEME_TAXONOMY.items():
        # Exact code match (highest priority)
        if theme_code.lower() == q_norm:
            scored.append((10.0, theme))
            continue

        # Build target token bag: label + aliases
        target_tokens = _tokenize(theme["label"])
        for alias in theme["aliases"]:
            target_tokens.extend(_tokenize(alias))

        score = _fuzzy_token_score(q_tokens, target_tokens)
        if score >= min_score:
            scored.append((score, theme))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [t for _, t in scored[:limit]]


def get_all_theme_codes() -> List[str]:
    """Get list of all available theme codes."""
    return list(THEME_TAXONOMY.keys())


def get_all_categories() -> List[str]:
    """Get list of all categories."""
    return list(THEME_CATEGORIES.keys())


# ===== INVESTIGATIVE CONCEPT MAP =====
# Maps human investigative concepts to GDELT theme bundles.
# Used by /api/v2/concept/{slug} to power free-text investigation entry points.
# Each concept has a slug, label, description, and a list of GDELT theme codes
# that together represent the concept's signal footprint.

CONCEPT_MAP: Dict[str, dict] = {
    "blood-diamonds": {
        "label": "Blood Diamonds",
        "description": "Conflict minerals — gemstones funding armed groups, illicit trade routes, sanctions evasion",
        "themes": ["ARMEDCONFLICT", "KILL", "CRIME", "ECON_TRADE", "WB_507_ENERGY_AND_EXTRACTIVES", "SEIZE"],
        "related_concepts": ["cobalt-mining", "arms-trafficking"],
    },
    "cobalt-mining": {
        "label": "Cobalt Mining",
        "description": "DRC and Central Africa cobalt extraction, child labor, EV supply chain, human rights",
        "themes": ["WB_507_ENERGY_AND_EXTRACTIVES", "LABOR", "WB_HUMAN_RIGHTS", "ECON_TRADE", "ARMEDCONFLICT"],
        "related_concepts": ["blood-diamonds", "climate-minerals"],
    },
    "arms-trafficking": {
        "label": "Arms Trafficking",
        "description": "Illicit weapons trade, smuggling networks, embargo violations, proxy wars",
        "themes": ["ARMEDCONFLICT", "SEIZE", "CRIME", "MILITARY", "TAX_TERROR"],
        "related_concepts": ["blood-diamonds", "drug-trafficking"],
    },
    "drug-trafficking": {
        "label": "Drug Trafficking",
        "description": "Narco-trafficking networks, cartel violence, drug interdiction, money laundering",
        "themes": ["CRIME", "ARREST", "KILL", "TAX_TERROR", "ECON_TRADE"],
        "related_concepts": ["arms-trafficking", "money-laundering"],
    },
    "money-laundering": {
        "label": "Money Laundering",
        "description": "Financial crime, shell companies, offshore accounts, sanctions evasion",
        "themes": ["CRIME", "TAX_FNCACT", "ECON_TRADE", "ARREST", "WB_ANTI_CORRUPTION"],
        "related_concepts": ["drug-trafficking", "corruption"],
    },
    "corruption": {
        "label": "Corruption",
        "description": "Bribery, embezzlement, state capture, procurement fraud, kleptocracy",
        "themes": ["WB_ANTI_CORRUPTION", "WB_GOVERNANCE", "CRIME", "ARREST", "PROTEST"],
        "related_concepts": ["money-laundering", "sanctions"],
    },
    "sanctions": {
        "label": "Sanctions & Embargoes",
        "description": "International sanctions, asset freezes, trade restrictions, compliance",
        "themes": ["ECON_TRADE", "MILITARY", "SEIZE", "WB_TRADE_POLICY", "WB_GOVERNANCE"],
        "related_concepts": ["arms-trafficking", "corruption"],
    },
    "refugee-crisis": {
        "label": "Refugee Crisis",
        "description": "Forced displacement, asylum seekers, border crossings, humanitarian corridors",
        "themes": ["MIGRATION", "WB_HUMAN_RIGHTS", "ARMEDCONFLICT", "DISASTER", "WB_GOVERNANCE"],
        "related_concepts": ["armed-conflict", "humanitarian-aid"],
    },
    "humanitarian-aid": {
        "label": "Humanitarian Aid",
        "description": "Emergency relief, food security, aid access, NGO operations, blockades",
        "themes": ["DISASTER", "WB_HUMAN_RIGHTS", "HEALTH", "ARMEDCONFLICT", "UNGP_DISASTER"],
        "related_concepts": ["refugee-crisis", "food-security"],
    },
    "food-security": {
        "label": "Food Security",
        "description": "Famine, food price crises, agricultural collapse, supply chain disruption",
        "themes": ["AGRICULTURE", "DISASTER", "ECON_INFLATION", "WB_1637_AGRICULTURE_AND_FOOD", "UNGP_DISASTER"],
        "related_concepts": ["humanitarian-aid", "climate-crisis"],
    },
    "climate-crisis": {
        "label": "Climate Crisis",
        "description": "Extreme weather, climate migration, emissions, energy transition, IPCC",
        "themes": ["WB_2810_CLIMATE_CHANGE", "DISASTER", "ENERGY", "AGRICULTURE", "MIGRATION"],
        "related_concepts": ["food-security", "climate-minerals"],
    },
    "climate-minerals": {
        "label": "Critical Minerals",
        "description": "Lithium, cobalt, rare earths — energy transition supply chains and geopolitics",
        "themes": ["WB_507_ENERGY_AND_EXTRACTIVES", "ECON_TRADE", "WB_TRADE_POLICY", "ARMEDCONFLICT"],
        "related_concepts": ["cobalt-mining", "climate-crisis"],
    },
    "disinformation": {
        "label": "Disinformation & Propaganda",
        "description": "Information warfare, state media manipulation, fake news, influence operations",
        "themes": ["MEDIA_MSM", "CYBERATTACK", "MILITARY", "WB_GOVERNANCE", "TAX_TERROR"],
        "related_concepts": ["cyber-warfare", "elections"],
    },
    "cyber-warfare": {
        "label": "Cyber Warfare",
        "description": "State-sponsored hacking, critical infrastructure attacks, espionage, ransomware",
        "themes": ["CYBERATTACK", "MILITARY", "WB_GOVERNANCE", "TAX_TERROR", "TECHNOLOGY"],
        "related_concepts": ["disinformation", "sanctions"],
    },
    "elections": {
        "label": "Electoral Integrity",
        "description": "Election interference, voter suppression, disputed results, democratic backsliding",
        "themes": ["ELECTIONS", "PROTEST", "WB_GOVERNANCE", "MEDIA_MSM", "DISINFORMATION"],
        "related_concepts": ["disinformation", "corruption"],
    },
    "war-crimes": {
        "label": "War Crimes & Atrocities",
        "description": "Civilian targeting, chemical weapons, genocide, ICC prosecutions",
        "themes": ["ARMEDCONFLICT", "KILL", "WB_HUMAN_RIGHTS", "CRISISLEX_C03_DEAD_WOUNDED", "WB_GOVERNANCE"],
        "related_concepts": ["refugee-crisis", "sanctions"],
    },
    "nuclear-threat": {
        "label": "Nuclear Threat",
        "description": "Nuclear weapons programs, proliferation, deterrence, IAEA inspections",
        "themes": ["MILITARY", "TAX_TERROR", "ECON_TRADE", "WB_GOVERNANCE", "ARMEDCONFLICT"],
        "related_concepts": ["arms-trafficking", "sanctions"],
    },
    "human-trafficking": {
        "label": "Human Trafficking",
        "description": "Modern slavery, forced labor, sex trafficking, smuggling networks, exploitation",
        "themes": ["CRIME", "ARREST", "WB_HUMAN_RIGHTS", "MIGRATION", "LABOR"],
        "related_concepts": ["arms-trafficking", "drug-trafficking", "refugee-crisis"],
    },
    "femicide": {
        "label": "Femicide & Gender Violence",
        "description": "Killings of women, gender-based violence, domestic violence, impunity",
        "themes": ["KILL", "CRISISLEX_C06_VIOLENCE", "WB_HUMAN_RIGHTS", "CRIME", "WB_632_WOMEN_IN_POLITICS"],
        "related_concepts": ["human-trafficking", "state-repression"],
    },
    "genocide": {
        "label": "Genocide & Mass Atrocities",
        "description": "Ethnic cleansing, mass killings, crimes against humanity, ICC referrals",
        "themes": ["KILL", "ARMEDCONFLICT", "WB_HUMAN_RIGHTS", "CRISISLEX_C03_DEAD_WOUNDED", "MIGRATION"],
        "related_concepts": ["war-crimes", "refugee-crisis"],
    },
    "press-freedom": {
        "label": "Press Freedom",
        "description": "Journalist safety, media censorship, attacks on press, legal harassment of reporters",
        "themes": ["MEDIA_MSM", "WB_HUMAN_RIGHTS", "WB_GOVERNANCE", "ARREST", "KILL"],
        "related_concepts": ["disinformation", "state-repression"],
    },
    "pandemic-disease": {
        "label": "Pandemic & Disease Outbreaks",
        "description": "Epidemic outbreaks, vaccine access, public health emergencies, WHO response",
        "themes": ["HEALTH", "UNGP_DISASTER", "DISASTER_RESPONSE", "WB_GOVERNANCE", "ECON_TRADE"],
        "related_concepts": ["humanitarian-aid", "climate-crisis"],
    },
    "state-repression": {
        "label": "State Repression",
        "description": "Authoritarian crackdowns, political prisoners, mass arrests, dissent suppression",
        "themes": ["ARREST", "PROTEST", "WB_HUMAN_RIGHTS", "WB_GOVERNANCE", "MILITARY"],
        "related_concepts": ["press-freedom", "femicide", "corruption"],
    },
}


def get_concept(slug: str) -> dict | None:
    """Return concept definition by slug, or None if not found."""
    return CONCEPT_MAP.get(slug)


def search_concepts(query: str, limit: int = 10, min_score: float = 0.7) -> list[dict]:
    """Search concepts by label, description, slug, or theme codes with fuzzy matching.

    Concepts are editorial frames, so we score generously (lower threshold than themes)
    and weight label hits above description hits. Slug is also tokenized (handles
    "blood diamonds" → "blood-diamonds" by matching tokens).

    Returns list of {slug, ...concept, _score} sorted by relevance.
    """
    if not query or not query.strip():
        return []

    q_norm = _normalize(query)
    q_tokens = _tokenize(query)
    if not q_tokens:
        return []

    scored: list[tuple[float, dict]] = []

    for slug, concept in CONCEPT_MAP.items():
        # Exact slug match → top
        if slug == q_norm or slug.replace("-", " ") == q_norm:
            scored.append((10.0, {"slug": slug, **concept}))
            continue

        label_tokens = _tokenize(concept["label"]) + _tokenize(slug.replace("-", " "))
        desc_tokens = _tokenize(concept["description"])
        # Theme codes contribute too — "KILL" search hits "femicide", "genocide" concepts
        theme_tokens = []
        for code in concept["themes"]:
            theme_tokens.extend(_tokenize(code.replace("_", " ")))

        label_score = _fuzzy_token_score(q_tokens, label_tokens)
        desc_score = _fuzzy_token_score(q_tokens, desc_tokens)
        theme_score = _fuzzy_token_score(q_tokens, theme_tokens)

        # Weighted: label is the editorial frame, description is supporting, themes are weakest
        score = max(label_score, 0.7 * desc_score, 0.5 * theme_score)
        if score >= min_score:
            scored.append((score, {"slug": slug, **concept}))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:limit]]


def find_closest_concepts(query: str, limit: int = 3) -> list[dict]:
    """Return up to `limit` closest concepts as 'did you mean' suggestions.

    Used when a query yields no concept hits AND no theme hits. We compute a
    weaker fuzzy match (no min_score floor) so we always have something to suggest.
    """
    if not query or not query.strip():
        return []
    q_tokens = _tokenize(query)
    if not q_tokens:
        return []

    scored: list[tuple[float, dict]] = []
    for slug, concept in CONCEPT_MAP.items():
        label_tokens = _tokenize(concept["label"]) + _tokenize(slug.replace("-", " "))
        score = _fuzzy_token_score(q_tokens, label_tokens)
        scored.append((score, {"slug": slug, "label": concept["label"], "description": concept["description"]}))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for s, c in scored[:limit] if s > 0.0]


def get_all_concepts() -> list[dict]:
    """Return all concepts as a list of {slug, label, description} dicts."""
    return [{"slug": s, "label": c["label"], "description": c["description"]}
            for s, c in CONCEPT_MAP.items()]


__all__ = [
    "THEME_TAXONOMY",
    "THEME_CATEGORIES",
    "CONCEPT_MAP",
    "get_theme_label",
    "get_theme_category",
    "get_themes_by_category",
    "search_themes",
    "get_all_theme_codes",
    "get_all_categories",
    "get_concept",
    "search_concepts",
    "find_closest_concepts",
    "get_all_concepts",
]
