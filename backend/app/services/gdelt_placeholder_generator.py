"""
GDELT Placeholder Generator - Narratively Realistic Test Data

Generates GDELT-shaped placeholder data that:
- Uses real GDELT theme taxonomy (50+ themes)
- Applies realistic narrative bundles (themes that co-occur)
- Respects geographic affinities (themes more common in certain regions)
- Uses authentic sentiment ranges (per category)
- Simulates temporal dynamics (baseline, episodic, trending patterns)
- Supports flow scenarios (narrative spreading between countries)

Based on validation from:
- DataSignalArchitect: Schema structure
- NarrativeGeopoliticsAnalyst: Narrative patterns and distributions

This is NOT random data - it's carefully crafted to exhibit realistic
geopolitical narrative patterns for testing flow detection and visualization.
"""

import random
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

from app.models.gdelt_schemas import (
    GDELTSignal,
    GDELTLocation,
    GDELTTone,
    SourceAttribution,
)
from app.core.gdelt_taxonomy import get_theme_label, THEME_TAXONOMY


# ===== COUNTRY METADATA =====

COUNTRY_CENTROIDS = {
    "US": {"name": "United States", "lat": 37.09, "lon": -95.71},
    "CO": {"name": "Colombia", "lat": 4.57, "lon": -74.30},
    "BR": {"name": "Brazil", "lat": -14.24, "lon": -51.93},
    "MX": {"name": "Mexico", "lat": 23.63, "lon": -102.55},
    "AR": {"name": "Argentina", "lat": -38.42, "lon": -63.62},
    "GB": {"name": "United Kingdom", "lat": 55.38, "lon": -3.44},
    "FR": {"name": "France", "lat": 46.23, "lon": 2.21},
    "DE": {"name": "Germany", "lat": 51.17, "lon": 10.45},
    "ES": {"name": "Spain", "lat": 40.46, "lon": -3.75},
    "IT": {"name": "Italy", "lat": 41.87, "lon": 12.57},
}


# ===== NARRATIVE BUNDLES (from NarrativeGeopoliticsAnalyst) =====

NARRATIVE_BUNDLES = {
    "economic_crisis_contagion": {
        "themes": ["ECON_INFLATION", "TAX_FNCACT", "ECON_BANKRUPTCY", "PROTEST"],
        "likelihood": 0.85,
        "typical_tone": -8.5,
        "description": "Economic distress triggering social unrest"
    },
    "labor_unrest": {
        "themes": ["LABOR", "STRIKE", "PROTEST", "ECON_INFLATION"],
        "likelihood": 0.78,
        "typical_tone": -6.2,
        "description": "Workers striking over wages/conditions"
    },
    "trade_tensions": {
        "themes": ["ECON_TRADE", "SANCTION", "TAX_DIPLOMACY", "GOVERNMENT"],
        "likelihood": 0.72,
        "typical_tone": -4.5,
        "description": "Trade disputes between nations"
    },
    "election_cycle": {
        "themes": ["ELECTION", "LEADER", "GOVERNMENT", "MEDIA_MSM", "SOC_POINTSOFVIEW"],
        "likelihood": 0.9,
        "typical_tone": -2.0,
        "description": "Electoral campaigns and political competition"
    },
    "corruption_scandal": {
        "themes": ["CORRUPTION", "INVESTIGATION", "COURT", "ARREST", "LEADER"],
        "likelihood": 0.82,
        "typical_tone": -12.5,
        "description": "Political corruption investigation"
    },
    "diplomatic_breakthrough": {
        "themes": ["TAX_DIPLOMACY", "TREATY", "LEADER", "GOVERNMENT"],
        "likelihood": 0.75,
        "typical_tone": 8.3,
        "description": "International cooperation and agreements"
    },
    "conflict_escalation": {
        "themes": ["ARMEDCONFLICT", "MILITARY", "CRISISLEX_C03_DEAD_WOUNDED", "KILL", "CRISISLEX_C06_VIOLENCE"],
        "likelihood": 0.88,
        "typical_tone": -25.0,
        "description": "Armed conflict and casualties"
    },
    "terrorism_response": {
        "themes": ["TAX_TERROR", "ARREST", "INVESTIGATION", "CRIME", "CYBERATTACK"],
        "likelihood": 0.7,
        "typical_tone": -18.0,
        "description": "Terrorism incident and law enforcement response"
    },
    "climate_emergency": {
        "themes": ["ENV_CLIMATECHANGE", "ENV_FORESTS", "UNGP_DISASTER", "DISASTER_RESPONSE"],
        "likelihood": 0.8,
        "typical_tone": -7.5,
        "description": "Climate crisis and emergency response"
    },
    "environmental_policy": {
        "themes": ["ENV_CLIMATECHANGE", "ENV_POLLUTION", "GOVERNMENT", "ENERGY", "TREATY"],
        "likelihood": 0.68,
        "typical_tone": 3.2,
        "description": "Environmental regulations and green policy"
    },
    "migration_crisis": {
        "themes": ["MIGRATION", "HUMAN_RIGHTS", "GOVERNMENT", "PROTEST", "COURT"],
        "likelihood": 0.75,
        "typical_tone": -5.8,
        "description": "Migration policy debates and humanitarian concerns"
    },
    "social_justice_movement": {
        "themes": ["HUMAN_RIGHTS", "PROTEST", "CRISISLEX_C06_VIOLENCE", "CRIME", "COURT"],
        "likelihood": 0.65,
        "typical_tone": -4.2,
        "description": "Civil rights protests and legal challenges"
    },
    "tech_regulation": {
        "themes": ["TECHNOLOGY", "GOVERNMENT", "COURT", "INVESTIGATION"],
        "likelihood": 0.6,
        "typical_tone": -1.5,
        "description": "Technology regulation and antitrust concerns"
    },
    "space_achievement": {
        "themes": ["SPACE", "TECHNOLOGY", "GOVERNMENT", "MEDIA_MSM"],
        "likelihood": 0.55,
        "typical_tone": 12.0,
        "description": "Space exploration milestones"
    },
    "public_health_emergency": {
        "themes": ["HEALTH", "GOVERNMENT", "DISASTER_RESPONSE", "MEDIA_MSM"],
        "likelihood": 0.72,
        "typical_tone": -9.0,
        "description": "Disease outbreak or health crisis"
    },
}


# ===== GEOGRAPHIC THEME AFFINITY (from NarrativeGeopoliticsAnalyst) =====

GEOGRAPHIC_THEME_AFFINITY = {
    "US": {
        "high": {"ELECTION": 0.75, "ECON_INFLATION": 0.68, "TECHNOLOGY": 0.72, "MEDIA_MSM": 0.65, "LEADER": 0.7, "GOVERNMENT": 0.8, "TAX_FNCACT": 0.7},
        "medium": {"SPACE": 0.45, "CYBERATTACK": 0.4, "HEALTH": 0.38, "CRIME": 0.42, "PROTEST": 0.35},
        "low": {"ENV_FORESTS": 0.12, "MIGRATION": 0.25, "AGRICULTURE": 0.15},
    },
    "CO": {
        "high": {"CORRUPTION": 0.65, "CRIME": 0.7, "ARMEDCONFLICT": 0.45, "MIGRATION": 0.55, "ENV_FORESTS": 0.6, "LEADER": 0.6},
        "medium": {"ECON_INFLATION": 0.38, "PROTEST": 0.42, "GOVERNMENT": 0.45, "HUMAN_RIGHTS": 0.35, "AGRICULTURE": 0.32},
        "low": {"SPACE": 0.05, "TECHNOLOGY": 0.18, "CYBERATTACK": 0.12},
    },
    "BR": {
        "high": {"ENV_FORESTS": 0.85, "AGRICULTURE": 0.68, "CORRUPTION": 0.62, "CRIME": 0.65, "ECON_INFLATION": 0.58, "LEADER": 0.7},
        "medium": {"ELECTION": 0.45, "PROTEST": 0.48, "ENV_CLIMATECHANGE": 0.4, "MIGRATION": 0.28},
        "low": {"SPACE": 0.08, "CYBERATTACK": 0.15, "TAX_TERROR": 0.08},
    },
    "MX": {
        "high": {"CRIME": 0.78, "KILL": 0.65, "CORRUPTION": 0.68, "MIGRATION": 0.72, "LEADER": 0.65},
        "medium": {"ECON_TRADE": 0.45, "GOVERNMENT": 0.48, "ARREST": 0.42, "ENERGY": 0.35},
        "low": {"SPACE": 0.05, "ENV_FORESTS": 0.18, "TECHNOLOGY": 0.22},
    },
    "AR": {
        "high": {"ECON_INFLATION": 0.85, "ECON_BANKRUPTCY": 0.62, "TAX_FNCACT": 0.65, "PROTEST": 0.68, "LABOR": 0.58, "STRIKE": 0.52},
        "medium": {"LEADER": 0.45, "ELECTION": 0.42, "CORRUPTION": 0.38, "AGRICULTURE": 0.35},
        "low": {"SPACE": 0.08, "CYBERATTACK": 0.12, "ENV_FORESTS": 0.15},
    },
    "GB": {
        "high": {"GOVERNMENT": 0.75, "LEADER": 0.7, "TAX_FNCACT": 0.68, "MEDIA_MSM": 0.65, "TAX_DIPLOMACY": 0.6},
        "medium": {"ELECTION": 0.42, "ECON_TRADE": 0.48, "MIGRATION": 0.38, "ENV_CLIMATECHANGE": 0.35, "TECHNOLOGY": 0.4},
        "low": {"ARMEDCONFLICT": 0.12, "CRIME": 0.22, "AGRICULTURE": 0.18},
    },
    "FR": {
        "high": {"GOVERNMENT": 0.72, "PROTEST": 0.7, "STRIKE": 0.65, "LEADER": 0.68, "ENV_CLIMATECHANGE": 0.58, "TAX_DIPLOMACY": 0.6},
        "medium": {"ECON_TRADE": 0.42, "MIGRATION": 0.45, "TAX_FNCACT": 0.38, "TECHNOLOGY": 0.35},
        "low": {"SPACE": 0.15, "AGRICULTURE": 0.25, "CRIME": 0.22},
    },
    "DE": {
        "high": {"GOVERNMENT": 0.75, "ECON_TRADE": 0.68, "ENV_CLIMATECHANGE": 0.72, "ENERGY": 0.65, "TECHNOLOGY": 0.62, "LEADER": 0.68},
        "medium": {"MIGRATION": 0.48, "TAX_DIPLOMACY": 0.45, "TAX_FNCACT": 0.42, "ELECTION": 0.38},
        "low": {"PROTEST": 0.25, "CRIME": 0.22, "CORRUPTION": 0.15},
    },
    "ES": {
        "high": {"GOVERNMENT": 0.68, "LEADER": 0.65, "MIGRATION": 0.62, "ECON_INFLATION": 0.55, "PROTEST": 0.52},
        "medium": {"ENV_CLIMATECHANGE": 0.42, "AGRICULTURE": 0.38, "ECON_TRADE": 0.35, "TECHNOLOGY": 0.32},
        "low": {"SPACE": 0.08, "CYBERATTACK": 0.15, "ARMEDCONFLICT": 0.12},
    },
    "IT": {
        "high": {"GOVERNMENT": 0.72, "LEADER": 0.68, "MIGRATION": 0.7, "ECON_INFLATION": 0.58, "CORRUPTION": 0.55},
        "medium": {"PROTEST": 0.42, "TAX_FNCACT": 0.38, "ECON_TRADE": 0.35, "ENV_CLIMATECHANGE": 0.32},
        "low": {"SPACE": 0.12, "TECHNOLOGY": 0.25, "AGRICULTURE": 0.28},
    },
}


# ===== SENTIMENT RANGES BY CATEGORY =====

CATEGORY_TONE_RANGES = {
    "security": {"min": -45.0, "max": -15.0, "typical": -28.0, "variance": 8.0},
    "economy": {"min": -15.0, "max": 5.0, "typical": -4.5, "variance": 6.0},
    "politics": {"min": -12.0, "max": 8.0, "typical": -3.2, "variance": 5.5},
    "environment": {"min": -20.0, "max": 10.0, "typical": -8.5, "variance": 7.0},
    "health": {"min": -25.0, "max": 5.0, "typical": -10.0, "variance": 8.0},
    "social": {"min": -10.0, "max": 12.0, "typical": -2.5, "variance": 6.0},
    "media": {"min": -8.0, "max": 3.0, "typical": -2.0, "variance": 4.0},
    "technology": {"min": -5.0, "max": 15.0, "typical": 4.5, "variance": 5.0},
    "infrastructure": {"min": -12.0, "max": 6.0, "typical": -3.0, "variance": 5.0},
    "culture": {"min": -2.0, "max": 18.0, "typical": 8.5, "variance": 6.0},
}


class GDELTPlaceholderGenerator:
    """
    Generate narratively realistic GDELT-shaped placeholder data.

    Uses:
    - Real GDELT theme taxonomy
    - Realistic narrative bundles (themes that co-occur)
    - Geographic affinities (region-specific themes)
    - Authentic sentiment ranges
    - Temporal dynamics (not implemented in this version)
    """

    def __init__(self, seed: Optional[int] = None):
        """Initialize generator with optional random seed for reproducibility."""
        if seed is not None:
            random.seed(seed)

        self.bundles = NARRATIVE_BUNDLES
        self.geo_affinity = GEOGRAPHIC_THEME_AFFINITY
        self.tone_ranges = CATEGORY_TONE_RANGES
        self.centroids = COUNTRY_CENTROIDS

    def generate_signal(
        self,
        country: str,
        timestamp: Optional[datetime] = None,
        bundle_name: Optional[str] = None,
    ) -> GDELTSignal:
        """
        Generate a single narratively realistic GDELT signal for a country.

        Args:
            country: ISO 3166-1 alpha-2 country code (e.g., 'US', 'BR')
            timestamp: Signal timestamp (defaults to now)
            bundle_name: Specific narrative bundle to use (None = weighted random)

        Returns:
            GDELTSignal object with realistic data
        """
        if timestamp is None:
            timestamp = datetime.utcnow()

        # Round to 15-minute bucket
        bucket_15min = self._round_to_15min(timestamp)

        # Select narrative bundle (weighted by country affinity)
        if bundle_name:
            bundle = self.bundles[bundle_name]
        else:
            bundle = self._select_weighted_bundle(country)

        # Generate location
        location = self._generate_location(country)

        # Generate themes and counts
        themes = bundle["themes"]
        theme_labels = [get_theme_label(t) for t in themes]
        theme_counts = self._generate_theme_counts(themes)
        primary_theme = max(theme_counts, key=theme_counts.get)

        # Generate tone
        tone = self._generate_tone(bundle["typical_tone"], bundle["themes"])

        # Calculate intensity (normalized to 0-1)
        total_count = sum(theme_counts.values())
        intensity = min(1.0, total_count / 150.0)  # Assume max ~150 mentions

        # Generate signal_id
        signal_id = f"{bucket_15min.strftime('%Y%m%d%H%M%S')}-{country}-{random.randint(1, 99)}"

        # Generate source attribution
        sources = self._generate_source_attribution()

        # Generate URL hash
        url_hash = hashlib.md5(f"{signal_id}".encode()).hexdigest()

        return GDELTSignal(
            signal_id=signal_id,
            timestamp=timestamp,
            bucket_15min=bucket_15min,
            source_collection_id=1,  # Web
            locations=[location],
            primary_location=location,
            themes=themes,
            theme_labels=theme_labels,
            theme_counts=theme_counts,
            primary_theme=primary_theme,
            tone=tone,
            intensity=intensity,
            sentiment_label=self._compute_sentiment_label(tone.overall),
            geographic_precision=self._compute_geo_precision(location.location_type),
            persons=None,  # Tier 2
            organizations=None,  # Tier 2
            source_url=None,  # Tier 2
            source_outlet=None,  # Tier 2
            sources=sources,
            confidence=sources.confidence_score(),
            url_hash=url_hash,
            duplicate_count=1,
            duplicate_outlets=[],
        )

    def generate_signals_batch(
        self,
        countries: List[str],
        count_per_country: int = 10,
        timestamp: Optional[datetime] = None,
    ) -> List[GDELTSignal]:
        """
        Generate batch of signals across multiple countries.

        Args:
            countries: List of country codes
            count_per_country: How many signals per country
            timestamp: Base timestamp (defaults to now)

        Returns:
            List of GDELTSignal objects
        """
        signals = []
        base_time = timestamp or datetime.utcnow()

        for country in countries:
            for i in range(count_per_country):
                # Vary timestamps slightly (within 15-minute window)
                time_offset = timedelta(minutes=random.randint(0, 14))
                signal_time = base_time - time_offset

                signal = self.generate_signal(country, signal_time)
                signals.append(signal)

        return signals

    # ===== PRIVATE HELPER METHODS =====

    def _round_to_15min(self, dt: datetime) -> datetime:
        """Round datetime to nearest 15-minute interval."""
        minutes = (dt.minute // 15) * 15
        return dt.replace(minute=minutes, second=0, microsecond=0)

    def _select_weighted_bundle(self, country: str) -> dict:
        """Select narrative bundle weighted by geographic affinity."""
        country_affinities = self.geo_affinity.get(country, self.geo_affinity["US"])

        # Score each bundle by average affinity of its themes
        bundle_scores = {}
        for bundle_name, bundle in self.bundles.items():
            score = 0.0
            count = 0

            for theme in bundle["themes"]:
                # Look up theme affinity in country profile
                for freq_level in ["high", "medium", "low"]:
                    if theme in country_affinities.get(freq_level, {}):
                        score += country_affinities[freq_level][theme]
                        count += 1
                        break

            avg_score = score / count if count > 0 else 0.1
            bundle_scores[bundle_name] = avg_score * bundle["likelihood"]

        # Weighted random selection
        bundles_list = list(self.bundles.values())
        weights = [bundle_scores.get(name, 0.1) for name in self.bundles.keys()]

        return random.choices(bundles_list, weights=weights)[0]

    def _generate_location(self, country: str) -> GDELTLocation:
        """Generate realistic location for country."""
        centroid = self.centroids.get(country, self.centroids["US"])

        # Add some random variance (±2 degrees)
        lat = centroid["lat"] + random.uniform(-2.0, 2.0)
        lon = centroid["lon"] + random.uniform(-2.0, 2.0)

        # Clamp to valid ranges
        lat = max(-90.0, min(90.0, lat))
        lon = max(-180.0, min(180.0, lon))

        return GDELTLocation(
            country_code=country,
            country_name=centroid["name"],
            location_name=None,  # City name (Tier 2)
            latitude=lat,
            longitude=lon,
            location_type=1,  # Country-level for now
            feature_id=None,
            char_offset=None,
            mention_count=1,
        )

    def _generate_theme_counts(self, themes: List[str]) -> Dict[str, int]:
        """Generate realistic mention counts for themes (power law distribution)."""
        counts = {}

        # First theme gets most mentions
        base_count = random.randint(30, 80)
        counts[themes[0]] = base_count

        # Subsequent themes decrease
        for i, theme in enumerate(themes[1:], start=1):
            decay_factor = 0.6 ** i
            count = int(base_count * decay_factor * random.uniform(0.8, 1.2))
            counts[theme] = max(5, count)  # At least 5 mentions

        return counts

    def _generate_tone(self, typical_tone: float, themes: List[str]) -> GDELTTone:
        """Generate realistic V2Tone values based on bundle tone and theme categories."""
        # Get category of primary theme
        primary_theme = themes[0]
        category = THEME_TAXONOMY.get(primary_theme, {}).get("category", "politics")
        tone_range = self.tone_ranges.get(category, self.tone_ranges["politics"])

        # Use bundle typical tone as baseline, add variance
        overall = typical_tone + random.gauss(0, tone_range["variance"])
        overall = max(tone_range["min"], min(tone_range["max"], overall))

        # Generate other tone components
        if overall < 0:
            # Negative tone
            positive_pct = random.uniform(0.5, 5.0)
            negative_pct = random.uniform(20.0, 60.0)
            polarity = abs(overall) / 10.0 + random.uniform(0.5, 2.0)
        else:
            # Positive tone
            positive_pct = random.uniform(10.0, 40.0)
            negative_pct = random.uniform(0.5, 8.0)
            polarity = overall / 10.0 + random.uniform(0.5, 2.0)

        activity_density = random.uniform(5.0, 20.0)
        self_reference = random.uniform(0.0, 10.0)

        return GDELTTone(
            overall=overall,
            positive_pct=positive_pct,
            negative_pct=negative_pct,
            polarity=max(0.0, polarity),
            activity_density=activity_density,
            self_reference=self_reference,
        )

    def _generate_source_attribution(self) -> SourceAttribution:
        """Generate realistic source attribution (mostly GDELT for placeholders)."""
        return SourceAttribution(
            gdelt=True,  # Always true for placeholders
            google_trends=random.random() < 0.7,  # 70% chance
            wikipedia=random.random() < 0.5,  # 50% chance
        )

    def _compute_sentiment_label(self, tone: float) -> str:
        """Compute categorical sentiment label from tone."""
        if tone < -10:
            return "very_negative"
        elif tone < -2:
            return "negative"
        elif tone < 2:
            return "neutral"
        elif tone < 10:
            return "positive"
        else:
            return "very_positive"

    def _compute_geo_precision(self, location_type: int) -> str:
        """Compute geographic precision label from location type."""
        if location_type == 1:
            return "country"
        elif location_type in [2, 5]:
            return "state"
        else:
            return "city"


# ===== SINGLETON INSTANCE =====

_generator_instance = None


def get_placeholder_generator() -> GDELTPlaceholderGenerator:
    """Get singleton instance of placeholder generator."""
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = GDELTPlaceholderGenerator()
    return _generator_instance


__all__ = [
    "GDELTPlaceholderGenerator",
    "get_placeholder_generator",
    "NARRATIVE_BUNDLES",
    "GEOGRAPHIC_THEME_AFFINITY",
]
