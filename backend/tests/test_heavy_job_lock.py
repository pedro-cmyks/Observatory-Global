"""Behavior tests for the P1.1 cross-runner heavy-job mutex."""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LOCK_SCRIPT = ROOT / "scripts" / "heavy-job-lock.sh"


def _run_lock(lock_dir: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "ATLAS_HEAVY_LOCK_DIR": str(lock_dir),
        "ATLAS_HEAVY_LOCK_LOG": str(lock_dir.parent / "heavy-lock.log"),
    }
    command = "source \"$1\"; shift; atlas_heavy_lock \"$@\""
    return subprocess.run(
        ["bash", "-c", command, "atlas-lock-test", str(LOCK_SCRIPT), *args],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def _write_holder(lock_dir: Path, *, pid: int, ttl: int, age_minutes: int) -> None:
    lock_dir.mkdir()
    started = int(time.time()) - age_minutes * 60
    (lock_dir / "info").write_text(
        f"pid={pid}\njob=scoped-snapshot\nstarted={started}\nttl={ttl}\n",
        encoding="utf-8",
    )


def test_short_ttl_contender_never_reclaims_live_long_job(tmp_path: Path) -> None:
    lock_dir = tmp_path / "atlas-heavy.lock"
    _write_holder(lock_dir, pid=os.getpid(), ttl=240, age_minutes=60)

    result = _run_lock(lock_dir, "matview-refresh", "skip", "45")

    assert result.returncode == 1
    assert lock_dir.is_dir()
    assert "SKIPPED" in result.stderr


def test_dead_holder_is_reclaimed(tmp_path: Path) -> None:
    lock_dir = tmp_path / "atlas-heavy.lock"
    _write_holder(lock_dir, pid=999_999, ttl=240, age_minutes=1)

    result = _run_lock(lock_dir, "matview-refresh", "skip", "45")

    assert result.returncode == 0
    assert "DEAD" in result.stderr


def test_new_owner_persists_its_own_ttl(tmp_path: Path) -> None:
    lock_dir = tmp_path / "atlas-heavy.lock"
    env = {
        **os.environ,
        "ATLAS_HEAVY_LOCK_DIR": str(lock_dir),
        "ATLAS_HEAVY_LOCK_LOG": str(tmp_path / "heavy-lock.log"),
    }
    command = (
        "source \"$1\"; "
        "atlas_heavy_lock scoped-snapshot skip 240; "
        "grep '^ttl=240$' \"$ATLAS_HEAVY_LOCK_DIR/info\"; rc=$?; "
        "_ATLAS_HEAVY_LOCK_HELD=''; exit $rc"
    )

    result = subprocess.run(
        ["bash", "-c", command, "atlas-lock-test", str(LOCK_SCRIPT)],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "ttl=240" in result.stdout
