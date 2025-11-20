"""Flow detection service using TF-IDF and exponential decay."""

import math
import logging
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from app.models.schemas import Topic
from app.models.flows import Hotspot, Flow, TopicSummary
from app.models.gdelt_schemas import GDELTSignal
from app.core.config import settings
from app.core.country_metadata import COUNTRY_METADATA

logger = logging.getLogger(__name__)


class FlowDetector:
    """Detects information flows between countries using TF-IDF and time decay."""

    def __init__(
        self,
        heat_halflife_hours: float = 6.0,
        flow_threshold: float = 0.5,
    ):
        """
        Initialize flow detector.

        Args:
            heat_halflife_hours: Half-life for exponential decay (default: 6 hours)
            flow_threshold: Minimum heat score to include flow (default: 0.5)
        """
        self.heat_halflife_hours = heat_halflife_hours
        self.flow_threshold = flow_threshold
        logger.info(
            f"FlowDetector initialized: halflife={heat_halflife_hours}h, threshold={flow_threshold}"
        )

    def calculate_similarity(self, topics_a: List[str], topics_b: List[str]) -> float:
        """
        Calculate TF-IDF cosine similarity between two lists of topics.

        Args:
            topics_a: List of topic labels from country A
            topics_b: List of topic labels from country B

        Returns:
            Maximum cosine similarity between any pair of topics [0, 1]
        """
        if not topics_a or not topics_b:
            return 0.0

        try:
            # Combine all topics for vectorization
            all_topics = topics_a + topics_b

            # Create TF-IDF vectorizer with bigrams and English stop words
            vectorizer = TfidfVectorizer(
                ngram_range=(1, 2),
                stop_words="english",
                lowercase=True,
                max_features=1000,
            )

            # Fit and transform
            tfidf_matrix = vectorizer.fit_transform(all_topics)

            # Split back into country A and country B
            matrix_a = tfidf_matrix[: len(topics_a)]
            matrix_b = tfidf_matrix[len(topics_a) :]

            # Calculate cosine similarity matrix
            similarity_matrix = cosine_similarity(matrix_a, matrix_b)

            # Return maximum similarity (best topic match), clamped to [0, 1]
            max_similarity = float(np.max(similarity_matrix))
            max_similarity = min(1.0, max(0.0, max_similarity))  # Clamp to handle floating point errors

            logger.debug(
                f"Similarity calculated: {max_similarity:.3f} "
                f"(topics_a={len(topics_a)}, topics_b={len(topics_b)})"
            )

            return max_similarity

        except Exception as e:
            logger.error(f"Error calculating similarity: {e}", exc_info=True)
            return 0.0

    def calculate_time_decay(self, delta_hours: float) -> float:
        """
        Calculate exponential time decay factor.

        Formula: exp(-Δt / halflife)

        Args:
            delta_hours: Time difference in hours

        Returns:
            Decay factor [0, 1]
        """
        if delta_hours < 0:
            delta_hours = 0

        decay = math.exp(-delta_hours / self.heat_halflife_hours)
        return decay

    def calculate_heat(self, similarity: float, time_delta_hours: float) -> float:
        """
        Calculate flow heat score.

        Formula: heat = similarity × exp(-Δt / halflife)

        Args:
            similarity: TF-IDF cosine similarity [0, 1]
            time_delta_hours: Time difference in hours

        Returns:
            Heat score [0, 1]
        """
        decay = self.calculate_time_decay(time_delta_hours)
        heat = similarity * decay

        logger.debug(
            f"Heat calculated: {heat:.3f} "
            f"(similarity={similarity:.3f}, delta={time_delta_hours:.1f}h, decay={decay:.3f})"
        )

        return heat

    def calculate_hotspot_intensity(
        self,
        topics: List[Topic],
        volume_weight: float = 0.4,
        velocity_weight: float = 0.3,
        confidence_weight: float = 0.3,
    ) -> float:
        """
        Calculate hotspot intensity from topics.

        Intensity = volume_weight × volume_score +
                   velocity_weight × velocity_score +
                   confidence_weight × avg_confidence

        Args:
            topics: List of trending topics
            volume_weight: Weight for topic count (default: 0.4)
            velocity_weight: Weight for velocity/change rate (default: 0.3)
            confidence_weight: Weight for average confidence (default: 0.3)

        Returns:
            Intensity score [0, 1]
        """
        if not topics:
            return 0.0

        # Volume score: normalize topic count (assume max 100 topics)
        volume_score = min(len(topics) / 100.0, 1.0)

        # Velocity score: use average count normalized (assume max count 1000)
        avg_count = sum(t.count for t in topics) / len(topics)
        velocity_score = min(avg_count / 1000.0, 1.0)

        # Confidence score: average confidence of all topics
        avg_confidence = sum(t.confidence for t in topics) / len(topics)

        # Weighted combination
        intensity = (
            volume_weight * volume_score
            + velocity_weight * velocity_score
            + confidence_weight * avg_confidence
        )

        logger.debug(
            f"Hotspot intensity: {intensity:.3f} "
            f"(volume={volume_score:.2f}, velocity={velocity_score:.2f}, conf={avg_confidence:.2f})"
        )

        return min(intensity, 1.0)

    def calculate_intensity_from_signals(self, signals: List[GDELTSignal]) -> float:
        """
        Calculate hotspot intensity using pre-computed GDELT signal intensities.

        This method uses the actual signal data instead of derived Topic counts,
        providing more accurate and varied intensity scores.

        Args:
            signals: List of GDELT signals for a country

        Returns:
            Average intensity score [0, 1]
        """
        if not signals:
            return 0.0

        # Use pre-computed intensity from signals (already normalized 0-1)
        avg_intensity = sum(s.intensity for s in signals) / len(signals)

        logger.debug(
            f"Signal-based intensity: {avg_intensity:.3f} from {len(signals)} signals"
        )

        return min(avg_intensity, 1.0)

    def detect_flows(
        self,
        trends_by_country: Dict[str, Tuple[List[Topic], datetime]],
        time_window_hours: float = 24.0,
        signals_by_country: Optional[Dict[str, List[GDELTSignal]]] = None,
    ) -> Tuple[List[Hotspot], List[Flow], Dict]:
        """
        Detect flows between countries based on trending topics.

        Args:
            trends_by_country: Dict mapping country code to (topics, timestamp)
            time_window_hours: Maximum time window for flow detection (default: 24h)
            signals_by_country: Optional dict of original GDELT signals for intensity calculation

        Returns:
            Tuple of (hotspots, flows, metadata)
        """
        logger.info(
            f"Detecting flows for {len(trends_by_country)} countries, "
            f"time_window={time_window_hours}h"
        )

        hotspots = []
        flows = []
        total_flows_computed = 0

        # Calculate hotspots for each country
        for country, (topics, timestamp) in trends_by_country.items():
            if not topics:
                continue

            # Use signal-based intensity if available, otherwise fall back to topic-based
            if signals_by_country and country in signals_by_country:
                intensity = self.calculate_intensity_from_signals(signals_by_country[country])
            else:
                intensity = self.calculate_hotspot_intensity(topics)

            # Get country metadata
            metadata = COUNTRY_METADATA.get(country)
            if not metadata:
                logger.warning(f"No metadata for country {country}, skipping")
                continue

            country_name, latitude, longitude = metadata

            # Calculate average confidence
            avg_confidence = sum(t.confidence for t in topics) / len(topics) if topics else 0.0

            # Get top 5 topics for hotspot display
            top_topics_sorted = sorted(topics, key=lambda t: t.count, reverse=True)[:5]
            top_topics = [
                TopicSummary(
                    label=t.label,
                    count=t.count,
                    confidence=t.confidence,
                )
                for t in top_topics_sorted
            ]

            hotspot = Hotspot(
                country_code=country,
                country_name=country_name,
                latitude=latitude,
                longitude=longitude,
                intensity=intensity,
                topic_count=len(topics),
                confidence=avg_confidence,
                top_topics=top_topics,
            )
            hotspots.append(hotspot)

        # Sort hotspots by intensity
        hotspots.sort(key=lambda h: h.intensity, reverse=True)

        # Detect flows between all country pairs
        country_list = list(trends_by_country.keys())

        for i, country_a in enumerate(country_list):
            for country_b in country_list[i + 1 :]:
                topics_a, timestamp_a = trends_by_country[country_a]
                topics_b, timestamp_b = trends_by_country[country_b]

                if not topics_a or not topics_b:
                    continue

                # Calculate time delta
                time_delta = abs((timestamp_b - timestamp_a).total_seconds()) / 3600.0

                # Skip if outside time window
                if time_delta > time_window_hours:
                    continue

                # Extract topic labels for similarity calculation
                labels_a = [t.label for t in topics_a]
                labels_b = [t.label for t in topics_b]

                # Calculate similarity
                similarity = self.calculate_similarity(labels_a, labels_b)

                # Calculate heat
                heat = self.calculate_heat(similarity, time_delta)

                total_flows_computed += 1

                # Filter by threshold
                if heat < self.flow_threshold:
                    continue

                # Determine flow direction (earlier -> later)
                if timestamp_a <= timestamp_b:
                    from_country = country_a
                    to_country = country_b
                else:
                    from_country = country_b
                    to_country = country_a

                # Find shared topics (simplified: top matching topics)
                # In production, would use actual similarity matrix
                shared_topics = self._find_shared_topics(labels_a, labels_b, limit=3)

                # Get coordinates for both countries
                from_metadata = COUNTRY_METADATA.get(from_country)
                to_metadata = COUNTRY_METADATA.get(to_country)

                if not from_metadata or not to_metadata:
                    logger.warning(f"Missing metadata for flow {from_country} -> {to_country}, skipping")
                    continue

                from_coords = [from_metadata[2], from_metadata[1]]  # [lng, lat]
                to_coords = [to_metadata[2], to_metadata[1]]  # [lng, lat]

                flow = Flow(
                    from_country=from_country,
                    to_country=to_country,
                    heat=heat,
                    similarity=similarity,
                    time_delta_minutes=time_delta * 60.0,  # Convert hours to minutes
                    shared_topics=shared_topics,
                    from_coords=from_coords,
                    to_coords=to_coords,
                )
                flows.append(flow)

        # Sort flows by heat
        flows.sort(key=lambda f: f.heat, reverse=True)

        metadata = {
            "formula": f"heat = similarity × exp(-Δt / {self.heat_halflife_hours}h)",
            "threshold": self.flow_threshold,
            "time_window_hours": time_window_hours,
            "total_flows_computed": total_flows_computed,
            "flows_returned": len(flows),
            "countries_analyzed": country_list,
        }

        logger.info(
            f"Flow detection complete: {len(hotspots)} hotspots, "
            f"{len(flows)}/{total_flows_computed} flows (filtered by threshold={self.flow_threshold})"
        )

        return hotspots, flows, metadata

    def _find_shared_topics(
        self, topics_a: List[str], topics_b: List[str], limit: int = 3
    ) -> List[str]:
        """
        Find shared/similar topics between two lists.

        Simple implementation: exact matches first, then truncated matches.

        Args:
            topics_a: Topics from country A
            topics_b: Topics from country B
            limit: Maximum number of shared topics to return

        Returns:
            List of shared topic labels
        """
        shared = []

        # Find exact matches
        set_a = {t.lower() for t in topics_a}
        set_b = {t.lower() for t in topics_b}
        exact_matches = set_a & set_b

        for match in list(exact_matches)[:limit]:
            # Return original casing
            for topic in topics_a:
                if topic.lower() == match:
                    shared.append(topic)
                    break

        # If not enough exact matches, find partial matches
        if len(shared) < limit:
            for topic_a in topics_a:
                if len(shared) >= limit:
                    break
                for topic_b in topics_b:
                    if topic_a.lower() in topic_b.lower() or topic_b.lower() in topic_a.lower():
                        if topic_a not in shared and topic_b not in shared:
                            shared.append(topic_a)
                            break

        return shared[:limit]


def parse_time_window(time_window_str: str) -> float:
    """
    Parse time window string to hours.

    Supported formats: '1h', '6h', '12h', '24h', '48h'

    Args:
        time_window_str: Time window string

    Returns:
        Hours as float

    Raises:
        ValueError: If format is invalid
    """
    time_window_str = time_window_str.strip().lower()

    if time_window_str.endswith("h"):
        try:
            hours = float(time_window_str[:-1])
            if hours <= 0:
                raise ValueError("Time window must be positive")
            return hours
        except ValueError as e:
            raise ValueError(f"Invalid time window format: {time_window_str}") from e
    else:
        raise ValueError(f"Time window must end with 'h' (hours): {time_window_str}")
