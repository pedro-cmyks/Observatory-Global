#!/usr/bin/env python3
"""Adaptive NLP-worker fleet supervisor for the M1 (#184 throughput).

Goal: drive NER true-output toward ingest (output == input) by running MANY
workers when Pedro's machine is idle, and falling back to ONE mindful worker the
moment he's using it again — never freeze the machine during working hours.

How it stays safe:
- GENTLE mode (Pedro active / on battery): 1 worker, no sharding, wrapped in
  `taskpolicy -b` (background QoS -> efficiency cores) + nice. Covers all recent
  signals slowly; yields to foreground work. This is the current behaviour.
- BURST mode (machine idle on AC power): N workers, each pinned to a disjoint
  id-shard (NLP_WORKER_SHARD_COUNT=N, NLP_WORKER_SHARD_INDEX=0..N-1 — verified
  even/disjoint partition of the backlog), at normal priority so they use the
  performance cores and drain the backlog as fast as the box allows.

Idle is measured from the HID input-idle time (seconds since last keyboard/mouse
event); power from `pmset`. The supervisor re-evaluates every CHECK_INTERVAL
seconds, so when Pedro touches the machine it drops back to GENTLE within that
window. A mode switch tears the current fleet down and brings the new one up
(the shard count differs between modes, so all workers must agree on N).

launchd runs THIS process (KeepAlive); it owns the worker children. On SIGTERM
it kills the fleet and exits cleanly.

Env knobs (all optional):
  NLP_FLEET_BURST_WORKERS     default 2   (workers in burst mode; M1 is 8GB and
                                           each loads ~1.5GB of models — 2 is the
                                           safe ceiling, bump only if RAM allows)
  NLP_FLEET_IDLE_SECONDS      default 180 (idle seconds before bursting)
  NLP_FLEET_CHECK_SECONDS     default 30  (re-evaluate cadence / switch-back lag)
  NLP_FLEET_REQUIRE_AC        default 1   (only burst on AC power)
  NLP_FLEET_WORKER_LIMIT      default 300 (per-cycle batch limit per worker)
  ATLAS_NLP_VENV_PY           default <root>/mlvenv/bin/python
  ATLAS_LOCAL_WORKER_DIR      default /Users/pedro/AtlasLocalWorker
"""
from __future__ import annotations

import os
import re
import signal
import subprocess
import sys
import time

WORKER_ROOT = os.getenv("ATLAS_LOCAL_WORKER_DIR", "/Users/pedro/AtlasLocalWorker")
BACKEND_DIR = os.getenv("ATLAS_NLP_BACKEND_DIR", os.path.join(WORKER_ROOT, "backend"))
VENV_PY = os.getenv("ATLAS_NLP_VENV_PY", os.path.join(WORKER_ROOT, "mlvenv", "bin", "python"))

BURST_WORKERS = max(2, int(os.getenv("NLP_FLEET_BURST_WORKERS", "2")))
IDLE_SECONDS = int(os.getenv("NLP_FLEET_IDLE_SECONDS", "180"))
CHECK_SECONDS = int(os.getenv("NLP_FLEET_CHECK_SECONDS", "30"))
REQUIRE_AC = os.getenv("NLP_FLEET_REQUIRE_AC", "1").lower() not in {"0", "false", "no"}
WORKER_LIMIT = os.getenv("NLP_FLEET_WORKER_LIMIT", "300")


def log(msg: str) -> None:
    print(f"[{time.strftime('%F %T')}] fleet: {msg}", flush=True)


def user_idle_seconds() -> float:
    """Seconds since the last HID (keyboard/mouse) event. inf on failure-safe."""
    try:
        out = subprocess.run(
            ["/usr/sbin/ioreg", "-c", "IOHIDSystem"],
            capture_output=True, text=True, timeout=10,
        ).stdout
        m = re.search(r'"HIDIdleTime"\s*=\s*(\d+)', out)
        if m:
            return int(m.group(1)) / 1_000_000_000.0  # ns -> s
    except Exception as exc:  # noqa: BLE001
        log(f"idle probe failed ({exc}); assuming ACTIVE")
    return 0.0  # fail safe: treat as active -> gentle


def on_ac_power() -> bool:
    try:
        out = subprocess.run(
            ["/usr/bin/pmset", "-g", "batt"], capture_output=True, text=True, timeout=10
        ).stdout
        return "AC Power" in out
    except Exception:  # noqa: BLE001
        return True  # fail safe: assume plugged in


def desired_mode() -> str:
    idle = user_idle_seconds()
    if idle < IDLE_SECONDS:
        return "gentle"
    if REQUIRE_AC and not on_ac_power():
        return "gentle"
    return "burst"


def _worker_env(shard_count: int, shard_index: int) -> dict:
    env = dict(os.environ)
    env.update({
        "NLP_WORKER_SHARD_COUNT": str(shard_count),
        "NLP_WORKER_SHARD_INDEX": str(shard_index),
        "NLP_WORKER_NER_ENABLED": "true",
        "NLP_FAST_LANE_ENABLED": "false",   # Fly owns the sentiment fast-lane
        "EMBED_SERVICE_ENABLED": "false",   # embed stays on Fly
        "NLP_WORKER_ID": f"m1-shard{shard_index}of{shard_count}",
    })
    return env


def spawn_worker(shard_count: int, shard_index: int, mindful: bool) -> subprocess.Popen:
    """Start one worker. mindful=True -> background QoS (efficiency cores)."""
    py = [VENV_PY, "-m", "enrichment.nlp_worker", "--limit", WORKER_LIMIT]
    if mindful:
        cmd = ["/usr/bin/nice", "-n", "10", "/usr/sbin/taskpolicy", "-b", *py]
    else:
        cmd = ["/usr/bin/nice", "-n", "5", *py]  # normal QoS -> performance cores
    return subprocess.Popen(cmd, cwd=BACKEND_DIR, env=_worker_env(shard_count, shard_index))


class Fleet:
    def __init__(self) -> None:
        self.mode: str | None = None
        self.procs: list[subprocess.Popen] = []

    def _kill_all(self) -> None:
        for p in self.procs:
            try:
                p.terminate()
            except Exception:  # noqa: BLE001
                pass
        deadline = time.time() + 20
        for p in self.procs:
            try:
                p.wait(timeout=max(0.5, deadline - time.time()))
            except Exception:  # noqa: BLE001
                try:
                    p.kill()
                except Exception:  # noqa: BLE001
                    pass
        self.procs = []

    def apply(self, mode: str) -> None:
        if mode == self.mode and all(p.poll() is None for p in self.procs):
            return  # already in mode and all alive
        if mode == self.mode:
            # same mode but a worker died — respawn just the dead shards
            n = len(self.procs)
            for i, p in enumerate(self.procs):
                if p.poll() is not None:
                    log(f"respawning dead shard {i}/{n}")
                    self.procs[i] = spawn_worker(n, i, mindful=(mode == "gentle"))
            return
        log(f"switching {self.mode} -> {mode}")
        self._kill_all()
        if mode == "gentle":
            self.procs = [spawn_worker(1, 0, mindful=True)]
        else:
            self.procs = [spawn_worker(BURST_WORKERS, i, mindful=False)
                          for i in range(BURST_WORKERS)]
        self.mode = mode
        log(f"mode={mode} workers={len(self.procs)}")

    def shutdown(self, *_a) -> None:
        log("SIGTERM — tearing down fleet")
        self._kill_all()
        sys.exit(0)


def main() -> None:
    log(f"supervisor start (burst={BURST_WORKERS} idle>={IDLE_SECONDS}s "
        f"check={CHECK_SECONDS}s require_ac={REQUIRE_AC})")
    fleet = Fleet()
    signal.signal(signal.SIGTERM, fleet.shutdown)
    signal.signal(signal.SIGINT, fleet.shutdown)
    while True:
        try:
            fleet.apply(desired_mode())
        except Exception as exc:  # noqa: BLE001
            log(f"loop error: {exc}")
        time.sleep(CHECK_SECONDS)


if __name__ == "__main__":
    main()
