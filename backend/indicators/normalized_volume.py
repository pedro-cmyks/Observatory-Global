"""
Normalized Volume Indicator

Calculates volume metrics relative to historical baseline,
including multiplier (X times normal) and z-score.
"""

from typing import Dict, Any, Optional


def calculate_normalized_volume(
    current_count: int,
    baseline_avg: float,
    baseline_stddev: float
) -> Dict[str, Any]:
    """
    Calculate normalized volume metrics.
    
    Args:
        current_count: Number of signals in current time window
        baseline_avg: Average signal count over baseline period (e.g., 7-day rolling)
        baseline_stddev: Standard deviation over baseline period
    
    Returns:
        Dict with:
        - multiplier: current / baseline ratio (e.g., 2.5 means "2.5x normal")
        - z_score: standard deviations from baseline
        - current: current count (echo back)
        - baseline: baseline average (echo back)
        - level: 'exceptional', 'high', 'elevated', 'normal', 'low'
        - tooltip: explanation for UI
    """
    # Handle edge cases
    if baseline_avg == 0 or baseline_avg is None:
        return {
            "multiplier": None,
            "z_score": None,
            "current": current_count,
            "baseline": baseline_avg,
            "level": "unknown",
            "tooltip": "Insufficient baseline data to calculate normalized volume."
        }
    
    # Calculate multiplier
    multiplier = current_count / baseline_avg
    
    # Calculate z-score (handle zero stddev)
    if baseline_stddev and baseline_stddev > 0:
        z_score = (current_count - baseline_avg) / baseline_stddev
    else:
        # If no variance, any deviation is technically infinite
        # Use a reasonable approximation
        z_score = 0 if current_count == baseline_avg else (3 if current_count > baseline_avg else -3)
    
    # Determine level based on z-score
    if z_score > 3:
        level = "exceptional"
        level_desc = "Very unusual activity"
    elif z_score > 2:
        level = "high"
        level_desc = "Elevated activity"
    elif z_score > 1:
        level = "elevated"
        level_desc = "Above normal"
    elif z_score < -1:
        level = "low"
        level_desc = "Below normal"
    else:
        level = "normal"
        level_desc = "Within expected range"
    
    # Build tooltip
    tooltip = (
        f"{multiplier:.1f}x normal volume ({level_desc}). "
        f"Z-score: {z_score:.1f}. "
        f"Current: {current_count} signals, Baseline: {baseline_avg:.0f} signals/period (7-day average)."
    )
    
    return {
        "multiplier": round(multiplier, 2),
        "z_score": round(z_score, 2),
        "current": current_count,
        "baseline": round(baseline_avg, 1),
        "baseline_stddev": round(baseline_stddev, 1) if baseline_stddev else None,
        "level": level,
        "tooltip": tooltip
    }


def get_volume_level(z_score: float) -> str:
    """
    Get the volume level string from z-score.
    
    Args:
        z_score: Standard deviations from baseline
    
    Returns:
        Level string: 'exceptional', 'high', 'elevated', 'normal', 'low'
    """
    if z_score > 3:
        return "exceptional"
    elif z_score > 2:
        return "high"
    elif z_score > 1:
        return "elevated"
    elif z_score < -1:
        return "low"
    else:
        return "normal"


def get_level_color(level: str) -> str:
    """
    Get a suggested color for the volume level (for UI consistency).
    
    Args:
        level: Volume level string
    
    Returns:
        Color string (CSS color name or hex)
    """
    colors = {
        "exceptional": "#ef4444",  # red-500
        "high": "#f97316",         # orange-500
        "elevated": "#eab308",     # yellow-500
        "normal": "#22c55e",       # green-500
        "low": "#6b7280",          # gray-500
        "unknown": "#9ca3af"       # gray-400
    }
    return colors.get(level, colors["unknown"])


# Full tooltip text for API documentation
VOLUME_TOOLTIP = """
Normalized Volume

How it's calculated:
• Multiplier: Current signals ÷ 7-day average for same time-of-day
• Z-score: (Current - Baseline) ÷ Standard Deviation

Volume levels:
• Exceptional (z > 3): Very unusual activity, >3 standard deviations above normal
• High (z 2-3): Elevated activity, likely significant event
• Elevated (z 1-2): Above normal, may warrant attention
• Normal (z -1 to 1): Within expected daily variation
• Low (z < -1): Below normal activity

Note: Baselines are calculated using same hour-of-day to account for 
daily patterns (e.g., lower activity at night).
""".strip()
