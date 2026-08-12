"""
Normalized Volume Indicator

Calculates volume metrics relative to historical baseline,
including multiplier (X times normal) and z-score.
"""

import math
from typing import Dict, Any, Optional

#: Fewest daily observations that can support a sigma anyone should read.
#: East Timor's "z: 71.2" rested on six sparse days (cold-user probe 2026-08-12).
MIN_BASELINE_DAYS = 5
#: Smallest baseline average (signals per period) worth dividing by. Below this
#: the stddev is a rounding artifact and the quotient explodes.
MIN_BASELINE_AVG = 5.0


def scale_baseline_stddev(baseline_stddev: float, hours: int) -> float:
    """Scale a per-day sigma to an arbitrary window.

    The mean of a count over t days scales linearly with t; its standard
    deviation scales with sqrt(t). Scaling both linearly (the previous
    behaviour) left the multiplier invariant -- the factor cancels in a ratio --
    while dragging the z-score around with the window, so the two numbers on the
    country panel diverged further the more the reader touched the time control.
    """
    if not baseline_stddev or baseline_stddev <= 0:
        return 0.0
    if not hours or hours <= 0:
        return 0.0
    return baseline_stddev * math.sqrt(hours / 24)


def calculate_normalized_volume(
    current_count: int,
    baseline_avg: float,
    baseline_stddev: float,
    days_observed: Optional[int] = None,
    baseline_days: int = 7,
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
            "baseline_days": baseline_days,
            "days_observed": days_observed,
            "thin_baseline": True,
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
    
    # A baseline can be arithmetically valid and still be far too thin to carry
    # a sigma. Flag it so the surface degrades honestly instead of printing a
    # confident "z: 71.2" built on six sparse days of a 2.3/day country.
    thin_baseline = (
        not baseline_stddev
        or baseline_stddev <= 0
        or baseline_avg < MIN_BASELINE_AVG
        or (days_observed is not None and days_observed < MIN_BASELINE_DAYS)
    )

    # Build tooltip
    tooltip = (
        f"{multiplier:.1f}x normal volume ({level_desc}). "
        f"Z-score: {z_score:.1f}. "
        f"Current: {current_count} signals, Baseline: {baseline_avg:.0f} "
        f"signals/period ({baseline_days}-day average"
        f"{f', {days_observed} day(s) observed' if days_observed is not None else ''})."
    )
    if thin_baseline:
        tooltip += (
            " Baseline is too thin for a meaningful z-score -- treat the "
            "multiplier as the readable signal here."
        )

    return {
        "multiplier": round(multiplier, 2),
        "z_score": round(z_score, 2),
        "current": current_count,
        "baseline": round(baseline_avg, 1),
        "baseline_stddev": round(baseline_stddev, 1) if baseline_stddev else None,
        "baseline_days": baseline_days,
        "days_observed": days_observed,
        "thin_baseline": bool(thin_baseline),
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
