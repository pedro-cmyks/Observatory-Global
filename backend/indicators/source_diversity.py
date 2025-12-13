"""
Source Diversity Score Indicator

Calculates how diverse the sourcing is for a given set of signals,
based on unique domain count and distribution entropy.
"""

import math
from collections import Counter
from typing import List, Dict, Any


def calculate_source_diversity(domains: List[str]) -> Dict[str, Any]:
    """
    Calculate source diversity score based on domain distribution.
    
    Score components:
    - Unique domain count (0-50 points): more domains = higher score (logarithmic)
    - Distribution entropy (0-50 points): more even distribution = higher score
    
    Args:
        domains: List of domain names (can include duplicates)
    
    Returns:
        Dict with:
        - score: 0-100 overall diversity score
        - unique_count: number of unique domains
        - total_signals: total number of domains provided
        - top_domains: list of (domain, count) tuples for top 5
        - tooltip: explanation text for UI
        - breakdown: detailed score components
    """
    if not domains:
        return {
            "score": 0,
            "unique_count": 0,
            "total_signals": 0,
            "top_domains": [],
            "tooltip": "No sources available to calculate diversity.",
            "breakdown": {
                "unique_score": 0,
                "entropy_score": 0
            }
        }
    
    # Count occurrences
    counter = Counter(d.lower() for d in domains if d)
    unique_count = len(counter)
    total = len(domains)
    
    if unique_count == 0:
        return {
            "score": 0,
            "unique_count": 0,
            "total_signals": total,
            "top_domains": [],
            "tooltip": "No valid sources found.",
            "breakdown": {
                "unique_score": 0,
                "entropy_score": 0
            }
        }
    
    # Unique count score (0-50): logarithmic scale, caps at 20 unique sources
    # log(21) ≈ 3.04, so 20 sources = 50 points
    unique_score = min(50, (math.log(unique_count + 1) / math.log(21)) * 50)
    
    # Entropy score (0-50): normalized Shannon entropy
    if unique_count == 1:
        # Single source = 0 entropy
        entropy_score = 0
    else:
        # Calculate Shannon entropy
        entropy = -sum(
            (count / total) * math.log2(count / total) 
            for count in counter.values()
        )
        # Maximum possible entropy for this number of sources
        max_entropy = math.log2(unique_count)
        # Normalize to 0-50
        entropy_score = (entropy / max_entropy) * 50 if max_entropy > 0 else 0
    
    total_score = round(unique_score + entropy_score)
    
    # Get top domains
    top_domains = counter.most_common(5)
    
    # Build tooltip
    if total_score >= 80:
        quality = "Excellent"
    elif total_score >= 60:
        quality = "Good"
    elif total_score >= 40:
        quality = "Moderate"
    elif total_score >= 20:
        quality = "Limited"
    else:
        quality = "Poor"
    
    tooltip = (
        f"{quality} diversity ({total_score}/100). "
        f"Based on {unique_count} unique sources across {total} signals. "
        f"Higher scores indicate more sources with even coverage."
    )
    
    return {
        "score": total_score,
        "unique_count": unique_count,
        "total_signals": total,
        "top_domains": top_domains,
        "tooltip": tooltip,
        "breakdown": {
            "unique_score": round(unique_score, 1),
            "entropy_score": round(entropy_score, 1)
        }
    }


# Full tooltip text for API documentation
DIVERSITY_TOOLTIP = """
Source Diversity Score (0-100)

How it's calculated:
• 0-50 points: Number of unique domains (logarithmic scale, max at 20+ sources)
• 0-50 points: Distribution evenness (Shannon entropy, normalized)

Interpretation:
• 80-100: Excellent - Many sources with even coverage
• 60-79: Good - Solid source diversity
• 40-59: Moderate - Some concentration in few sources
• 20-39: Limited - Dominated by few sources
• 0-19: Poor - Single source or highly skewed

Note: High diversity doesn't guarantee accuracy, but reduces single-source bias.
""".strip()
