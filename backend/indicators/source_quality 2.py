"""
Source Quality Score Indicator

Calculates a transparent quality score based on source verification status.
Uses allowlist/denylist approach with clear scoring rules.
"""

from typing import List, Dict, Set, Any


# Verified news sources - major news agencies and established outlets
# This is NOT a truth judgment - these are sources with editorial standards
QUALITY_ALLOWLIST: Set[str] = {
    # Major wire services
    "reuters.com",
    "apnews.com",
    "afp.com",
    
    # Major English-language outlets
    "bbc.com",
    "bbc.co.uk",
    "nytimes.com",
    "washingtonpost.com",
    "theguardian.com",
    "economist.com",
    "ft.com",
    "wsj.com",
    "bloomberg.com",
    "cnn.com",
    "npr.org",
    "pbs.org",
    
    # International broadcasters
    "aljazeera.com",
    "dw.com",
    "france24.com",
    "nhk.or.jp",
    "abc.net.au",
    "cbc.ca",
    
    # Regional quality outlets
    "lemonde.fr",
    "spiegel.de",
    "elpais.com",
    "corriere.it",
    "scmp.com",
    "straitstimes.com",
    "thehindu.com",
    "japantimes.co.jp",
}

# Known aggregators - these syndicate content from other sources
# Adding to denylist to lower quality score (not block)
QUALITY_DENYLIST: Set[str] = {
    "yahoo.com",
    "msn.com",
    "flipboard.com",
    "biztoc.com",
    "smartnews.com",
    "feedly.com",
    "news.google.com",
    "apple.news",
}


def calculate_source_quality(domains: List[str]) -> Dict[str, Any]:
    """
    Calculate source quality score based on allowlist/denylist membership.
    
    Transparent scoring:
    - Base: 30 points for unknown sources (benefit of the doubt)
    - Each allowlisted source: +10 points (max 70 from allowlist)
    - Each denylisted source: -20 points
    - Final score clamped to 0-100
    
    Args:
        domains: List of domain names
    
    Returns:
        Dict with:
        - score: 0-100 quality score
        - allowlisted_count: number of verified sources
        - denylisted_count: number of flagged sources
        - unknown_count: number of unclassified sources
        - allowlisted_sources: list of verified sources present
        - tooltip: explanation for UI
    """
    if not domains:
        return {
            "score": 0,
            "allowlisted_count": 0,
            "denylisted_count": 0,
            "unknown_count": 0,
            "allowlisted_sources": [],
            "tooltip": "No sources available to assess quality."
        }
    
    # Normalize and dedupe
    unique_domains = set(d.lower().strip() for d in domains if d)
    
    # Classify each domain
    allowlisted = unique_domains & QUALITY_ALLOWLIST
    denylisted = unique_domains & QUALITY_DENYLIST
    unknown = unique_domains - QUALITY_ALLOWLIST - QUALITY_DENYLIST
    
    # Calculate score
    base_score = 30
    allowlist_bonus = min(70, len(allowlisted) * 10)
    denylist_penalty = len(denylisted) * 20
    
    raw_score = base_score + allowlist_bonus - denylist_penalty
    score = max(0, min(100, raw_score))
    
    # Build tooltip
    parts = []
    if allowlisted:
        parts.append(f"{len(allowlisted)} verified source(s)")
    if denylisted:
        parts.append(f"{len(denylisted)} flagged source(s)")
    if unknown:
        parts.append(f"{len(unknown)} unclassified source(s)")
    
    if score >= 80:
        quality = "High"
    elif score >= 50:
        quality = "Moderate"
    else:
        quality = "Low"
    
    tooltip = (
        f"{quality} quality score ({score}/100). "
        + ", ".join(parts) + ". "
        + "Verified sources include major wire services and established news outlets."
    )
    
    return {
        "score": score,
        "allowlisted_count": len(allowlisted),
        "denylisted_count": len(denylisted),
        "unknown_count": len(unknown),
        "allowlisted_sources": sorted(list(allowlisted))[:5],
        "tooltip": tooltip
    }


def get_allowlist() -> List[str]:
    """Return the current allowlist for transparency."""
    return sorted(list(QUALITY_ALLOWLIST))


def get_denylist() -> List[str]:
    """Return the current denylist for transparency."""
    return sorted(list(QUALITY_DENYLIST))


# Full tooltip text for API documentation
QUALITY_TOOLTIP = """
Source Quality Score (0-100)

How it's calculated:
• Base: 30 points (benefit of the doubt for unknown sources)
• Each verified source: +10 points (max +70)
• Each flagged source: -20 points

Verified sources include:
• Major wire services (Reuters, AP, AFP)
• Established international broadcasters (BBC, DW, Al Jazeera)
• Quality newspapers with editorial standards (NYT, Guardian, etc.)

Important caveats:
• This is a simple heuristic, not a truth judgment
• Even verified outlets can publish errors
• Unknown sources are not necessarily low quality
• The list is transparent and can be reviewed at /api/indicators/allowlist
""".strip()
