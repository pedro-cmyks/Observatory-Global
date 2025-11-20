"""
GDELT Signal to Topic Adapter

Converts GDELTSignal objects to Topic objects for backward compatibility
with the FlowDetector system.

This adapter is shared between flows.py and hexmap.py endpoints to eliminate
code duplication and ensure consistent conversion logic.
"""

import logging
from typing import Dict, List, Tuple
from datetime import datetime

from app.models.schemas import Topic
from app.models.gdelt_schemas import GDELTSignal

logger = logging.getLogger(__name__)


def gdelt_signal_to_topic(signal: GDELTSignal) -> Topic:
    """
    Convert GDELT signal to Topic for flow detector compatibility.

    This adapter ensures backward compatibility with the existing FlowDetector
    which expects Topic objects. Uses human-readable theme_labels (not raw GDELT codes).

    Args:
        signal: GDELTSignal object from fetch_gdelt_signals()

    Returns:
        Topic object compatible with FlowDetector
    """
    # Sum all theme counts to get total mention volume
    total_count = sum(signal.theme_counts.values()) if signal.theme_counts else 1

    # Use human-readable theme_labels (e.g., "Terrorism") not GDELT codes (e.g., "TAX_TERROR")
    primary_label = signal.theme_labels[0] if signal.theme_labels else signal.primary_theme

    return Topic(
        id=signal.signal_id,
        label=primary_label,
        count=total_count,
        sample_titles=[],  # GDELTSignal doesn't have sample_titles, leave empty
        sources=["gdelt"],
        confidence=signal.confidence
    )


def convert_gdelt_to_topics(
    signals_by_country: Dict[str, Tuple[List[GDELTSignal], datetime]]
) -> Tuple[Dict[str, Tuple[List[Topic], datetime]], Dict[str, List[GDELTSignal]]]:
    """
    Convert GDELT signals to Topics for all countries.

    Args:
        signals_by_country: Dict mapping country code to (signals, timestamp)

    Returns:
        Tuple of:
        - Dict mapping country code to (topics, timestamp) for FlowDetector
        - Dict mapping country code to original signals (for intensity calculation)
    """
    topics_by_country = {}
    signals_only = {}

    for country, (signals, timestamp) in signals_by_country.items():
        topics = [gdelt_signal_to_topic(signal) for signal in signals]
        topics_by_country[country] = (topics, timestamp)
        signals_only[country] = signals
        logger.debug(f"Converted {len(signals)} GDELT signals to Topics for {country}")

    return topics_by_country, signals_only
