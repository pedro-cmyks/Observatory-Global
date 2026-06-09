#!/usr/bin/env python3
"""Read-only Kalman-style state report for dynamic topics.

This does not classify topics and does not write to Atlas tables. It uses the
existing dynamic_topics membership history to estimate a smoothed intensity,
velocity, uncertainty, and surprise signal for each topic.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

ROUNDUP_PATTERNS = re.compile(
    r"\b(round\s?up|mixed news|miscellaneous|assorted|news brief|"
    r"various (news|stories|topics|updates)|grab\s?bag)\b",
    re.IGNORECASE,
)


def is_roundup_label(label: str | None) -> bool:
    if not label:
        return False
    return bool(ROUNDUP_PATTERNS.search(label))


@dataclass(frozen=True)
class Observation:
    snapshot_at: datetime
    n_signals: int
    cohesion: float | None = None
    noise_rate: float | None = None


@dataclass(frozen=True)
class StateEstimate:
    smoothed_intensity: float
    velocity: float
    uncertainty: float
    surprise: float
    trend: str
    n_observations: int


def _observed_intensity(n_signals: int) -> float:
    return math.log1p(max(int(n_signals), 0))


def _hours_between(left: datetime, right: datetime) -> float:
    return max((right - left).total_seconds() / 3600.0, 1.0)


def _measurement_variance(obs: Observation) -> float:
    variance = 0.35
    if obs.cohesion is not None:
        variance += max(0.0, 1.0 - float(obs.cohesion)) * 0.6
    if obs.noise_rate is not None:
        variance += max(0.0, float(obs.noise_rate)) * 0.8
    return max(variance, 0.05)


def estimate_state(observations: list[Observation]) -> StateEstimate:
    """Estimate level+velocity over log signal volume with a tiny Kalman filter."""
    ordered = sorted(observations, key=lambda o: o.snapshot_at)
    if not ordered:
        return StateEstimate(0.0, 0.0, 9.99, 0.0, "no_observations", 0)
    if len(ordered) == 1:
        return StateEstimate(
            smoothed_intensity=_observed_intensity(ordered[0].n_signals),
            velocity=0.0,
            uncertainty=2.0,
            surprise=0.0,
            trend="insufficient_history",
            n_observations=1,
        )

    x = np.array([_observed_intensity(ordered[0].n_signals), 0.0], dtype=np.float64)
    p = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float64)
    h = np.array([[1.0, 0.0]], dtype=np.float64)
    identity = np.eye(2, dtype=np.float64)
    max_surprise = 0.0

    previous = ordered[0]
    for obs in ordered[1:]:
        dt = _hours_between(previous.snapshot_at, obs.snapshot_at) / 6.0
        f = np.array([[1.0, dt], [0.0, 1.0]], dtype=np.float64)
        q = np.array([[0.06 * dt * dt, 0.0], [0.0, 0.05 * dt]], dtype=np.float64)

        predicted = f @ x
        p_pred = f @ p @ f.T + q
        z = np.array([_observed_intensity(obs.n_signals)], dtype=np.float64)
        r = np.array([[_measurement_variance(obs)]], dtype=np.float64)
        innovation = z - (h @ predicted)
        innovation_var = h @ p_pred @ h.T + r
        innovation_std = math.sqrt(float(innovation_var[0, 0]))
        if innovation_std > 0:
            max_surprise = max(max_surprise, abs(float(innovation[0])) / innovation_std)

        k = p_pred @ h.T @ np.linalg.inv(innovation_var)
        x = predicted + (k @ innovation)
        p = (identity - k @ h) @ p_pred
        previous = obs

    uncertainty = math.sqrt(max(float(p[0, 0]), 0.0))
    velocity = float(x[1])
    trend = _trend_label(velocity, max_surprise)
    return StateEstimate(
        smoothed_intensity=round(float(x[0]), 4),
        velocity=round(velocity, 4),
        uncertainty=round(uncertainty, 4),
        surprise=round(max_surprise, 4),
        trend=trend,
        n_observations=len(ordered),
    )


def _trend_label(velocity: float, surprise: float) -> str:
    if surprise >= 1.35 and velocity > 0.08:
        return "surging"
    if velocity > 0.05:
        return "accelerating"
    if velocity < -0.05:
        return "cooling"
    return "stable"


def build_topic_report(
    *,
    topic_id: int,
    label: str,
    lifecycle_state: str,
    current_noise_rate: float | None,
    current_agg_n_signals: int,
    observations: list[Observation],
) -> dict[str, Any]:
    estimate = estimate_state(observations)
    is_roundup = is_roundup_label(label)
    recommendation = _recommendation(lifecycle_state, current_noise_rate, estimate, is_roundup)
    return {
        "dynamic_topic_id": topic_id,
        "label": label,
        "lifecycle_state": lifecycle_state,
        "is_roundup": is_roundup,
        "current_noise_rate": current_noise_rate,
        "current_agg_n_signals": current_agg_n_signals,
        "observation_count": len(observations),
        "state_estimate": {
            "smoothed_intensity": estimate.smoothed_intensity,
            "velocity": estimate.velocity,
            "uncertainty": estimate.uncertainty,
            "surprise": estimate.surprise,
            "trend": estimate.trend,
            "n_observations": estimate.n_observations,
        },
        "recommendation": recommendation,
    }


def _recommendation(
    lifecycle_state: str,
    noise_rate: float | None,
    estimate: StateEstimate,
    is_roundup: bool,
) -> str:
    if estimate.n_observations < 2:
        return "collect_more_history"
    if is_roundup:
        return "do_not_promote_roundup"
    if noise_rate is not None and noise_rate >= 0.50:
        return "do_not_promote_high_noise"
    if estimate.trend in {"surging", "accelerating"} and lifecycle_state == "active":
        return "watch_acceleration"
    if estimate.trend == "cooling" and lifecycle_state == "active":
        return "watch_decay"
    return "keep_current_lifecycle"


async def load_topic_observations(conn, states: list[str], limit: int) -> list[dict[str, Any]]:
    rows = await conn.fetch(
        """
        SELECT
          dt.id AS dynamic_topic_id,
          dt.label,
          dt.state AS lifecycle_state,
          dt.noise_rate,
          dt.agg_n_signals,
          ec.snapshot_at,
          ec.n_signals,
          ec.cohesion,
          ec.role_noise_rate
        FROM dynamic_topics dt
        JOIN dynamic_topic_members dtm ON dtm.dynamic_topic_id = dt.id
        JOIN emergent_clusters ec ON ec.id = dtm.emergent_cluster_id
        WHERE dt.state = ANY($1::text[])
        ORDER BY dt.agg_n_signals DESC, dt.id, ec.snapshot_at
        """,
        states,
    )
    topics: dict[int, dict[str, Any]] = {}
    order: list[int] = []
    for row in rows:
        tid = int(row["dynamic_topic_id"])
        if tid not in topics:
            topics[tid] = {
                "topic_id": tid,
                "label": row["label"],
                "lifecycle_state": row["lifecycle_state"],
                "current_noise_rate": (
                    float(row["noise_rate"]) if row["noise_rate"] is not None else None
                ),
                "current_agg_n_signals": int(row["agg_n_signals"] or 0),
                "observations": [],
            }
            order.append(tid)
        topics[tid]["observations"].append(
            Observation(
                snapshot_at=row["snapshot_at"],
                n_signals=int(row["n_signals"] or 0),
                cohesion=float(row["cohesion"]) if row["cohesion"] is not None else None,
                noise_rate=(
                    float(row["role_noise_rate"]) if row["role_noise_rate"] is not None else None
                ),
            )
        )
    return [topics[tid] for tid in order[:limit]]


async def run(args: argparse.Namespace) -> dict[str, Any]:
    import asyncpg

    db = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not db:
        raise SystemExit("DATABASE_URL or SUPABASE_DB_URL required")
    states = [s.strip() for s in args.states.split(",") if s.strip()]
    conn = await asyncpg.connect(db)
    try:
        topic_inputs = await load_topic_observations(conn, states, args.limit)
    finally:
        await conn.close()

    reports = [build_topic_report(**topic) for topic in topic_inputs]
    return {
        "report_type": "dynamic-topic-kalman-state-pilot",
        "model_version": "kalman-state-v0-readonly",
        "read_only": True,
        "states": states,
        "topic_count": len(reports),
        "topics": reports,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Dynamic Topic State Pilot",
        "",
        f"**Model:** `{report['model_version']}`",
        "**Mode:** read-only; no lifecycle/classification writes.",
        "",
        "| topic | lifecycle | trend | velocity | surprise | uncertainty | recommendation |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for topic in report["topics"]:
        est = topic["state_estimate"]
        lines.append(
            "| {label} | {state} | {trend} | {velocity:.4f} | {surprise:.4f} | "
            "{uncertainty:.4f} | {recommendation} |".format(
                label=str(topic["label"]).replace("|", "\\|"),
                state=topic["lifecycle_state"],
                trend=est["trend"],
                velocity=est["velocity"],
                surprise=est["surprise"],
                uncertainty=est["uncertainty"],
                recommendation=topic["recommendation"],
            )
        )
    lines.extend(
        [
            "",
            "Interpretation: this report estimates movement state only. It should be used",
            "to prioritize review or monitoring, not to promote/suppress semantic topics.",
        ]
    )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only dynamic topic state report.")
    parser.add_argument("--states", default="active", help="Comma-separated dynamic topic states.")
    parser.add_argument("--limit", type=int, default=20, help="Maximum topics to report.")
    parser.add_argument("--output-json", help="Optional JSON output path.")
    parser.add_argument("--output-md", help="Optional Markdown output path.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = asyncio.run(run(args))
    payload = json.dumps(report, indent=2, ensure_ascii=False, default=str)
    if args.output_json:
        Path(args.output_json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output_json).write_text(payload + "\n", encoding="utf-8")
    if args.output_md:
        Path(args.output_md).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output_md).write_text(render_markdown(report), encoding="utf-8")
    if not args.output_json and not args.output_md:
        print(payload)


if __name__ == "__main__":
    main()
