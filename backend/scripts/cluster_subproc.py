"""EXECUTE-1 (2026-07-19) — hard-killable HDBSCAN via process isolation.

The brute-MST path (`hdbscan._hdbscan_linkage.mst_linkage_core_vector`) is a
single Cython loop with no signal checks — once entered it cannot be
interrupted from Python (the 07-19 forensics sampled the nightly run 7+ hours
INSIDE that call for one country). SIGALRM handlers, cancellation tokens and
watchdog threads are all useless against it; the only true wall-time
guarantee is a separate process the parent can SIGTERM/SIGKILL.

Contract:
  - spawn start method (fork is unsafe under the parent's asyncio/asyncpg);
  - arrays travel via .npy files in a private temp dir — NEVER the pipe (a
    >64KB queue put from a child that gets killed mid-write is the classic
    multiprocessing deadlock);
  - the child imports hdbscan lazily and calls the SAME `_cluster` wrapper
    the inline path uses (emergent_poc) — no algorithm duplication to drift;
  - `timeout_s > 0` → poll-join to a deadline, then terminate → kill →
    raise ClusterTimeout; `timeout_s <= 0` → isolated but unbounded (legacy);
  - ANY exit from the wait loop (exceptions, SIGTERM-as-SystemExit in the
    parent) kills the child via finally — a dead nightly run must never
    orphan a CPU-burning MST.

Import-light on purpose (numpy only at module level): the timeout machinery
is testable in the API .venv without hdbscan.
"""
from __future__ import annotations

import multiprocessing as mp
import os
import shutil
import sys
import tempfile
import time
import traceback
from pathlib import Path

import numpy as np


class ClusterTimeout(RuntimeError):
    """The clustering child exceeded its hard wall-time budget and was killed."""


def _write_npy_atomic(path: Path, arr: "np.ndarray") -> None:
    tmp = path.with_name(path.name + ".tmp.npy")
    np.save(tmp, arr)
    os.replace(tmp, path)


def _cluster_child(in_path: str, out_path: str, err_path: str,
                   mcs: int, ms: int, method: str) -> None:
    """Spawn target: load input, run the shared `_cluster`, save labels.

    Errors land in err_path (the parent surfaces them verbatim) — a silent
    nonzero exit would read as an unexplained failure at 3am."""
    try:
        arr = np.load(in_path)
        try:  # dual run-context, same as the callers
            from backend.scripts.emergent_poc import _cluster
        except ImportError:  # pragma: no cover
            from scripts.emergent_poc import _cluster
        labels = np.asarray(_cluster(arr, mcs, ms, method), dtype=np.int64)
        _write_npy_atomic(Path(out_path), labels)
    except BaseException:
        try:
            Path(err_path).write_text(traceback.format_exc(), encoding="utf-8")
        except Exception:
            pass
        sys.exit(1)


def _sleep_child(in_path: str, out_path: str, err_path: str,
                 mcs: int, ms: int, method: str) -> None:  # pragma: no cover
    """Test support: an uninterruptible-looking child (models the MST hang)."""
    time.sleep(30)


def _error_child(in_path: str, out_path: str, err_path: str,
                 mcs: int, ms: int, method: str) -> None:
    """Test support: a child that fails like a real in-child exception."""
    try:
        raise RuntimeError("boom-for-tests")
    except BaseException:
        Path(err_path).write_text(traceback.format_exc(), encoding="utf-8")
        sys.exit(1)


def run_cluster_in_subprocess(embs: "np.ndarray", mcs: int, ms: int,
                              method: str, timeout_s: float,
                              _target=_cluster_child) -> "np.ndarray":
    """Run `_cluster(embs, mcs, ms, method)` in a killable spawn child.

    Returns the labels array. Raises ClusterTimeout on deadline overrun
    (child killed first), RuntimeError on child failure."""
    workdir = Path(tempfile.mkdtemp(prefix="atlas-cluster-"))
    in_path = workdir / "in.npy"
    out_path = workdir / "labels.npy"
    err_path = workdir / "err.txt"
    proc: mp.process.BaseProcess | None = None
    try:
        _write_npy_atomic(in_path, np.ascontiguousarray(embs, dtype=np.float32))
        ctx = mp.get_context("spawn")
        proc = ctx.Process(
            target=_target,
            args=(str(in_path), str(out_path), str(err_path), mcs, ms, method),
            daemon=True,
        )
        proc.start()
        deadline = (time.monotonic() + timeout_s) if timeout_s and timeout_s > 0 \
            else None
        while proc.is_alive():
            if deadline is not None and time.monotonic() > deadline:
                raise ClusterTimeout(
                    f"clustering exceeded its {timeout_s:.0f}s hard budget "
                    f"(n={len(embs)}) — child killed")
            proc.join(0.5)
        if proc.exitcode != 0:
            detail = ""
            if err_path.exists():
                detail = err_path.read_text(encoding="utf-8").strip()
                detail = detail.splitlines()[-1] if detail else ""
            raise RuntimeError(
                f"cluster subprocess failed (exit={proc.exitcode})"
                + (f": {detail}" if detail else ""))
        if not out_path.exists():
            raise RuntimeError("cluster subprocess exited 0 without labels")
        return np.load(out_path)
    finally:
        # ANY exit path — timeout, parent exception, SIGTERM-as-SystemExit —
        # must leave no orphan MST burning the machine for hours.
        if proc is not None and proc.is_alive():
            proc.terminate()
            proc.join(10)
            if proc.is_alive():  # pragma: no cover — SIGTERM-immune child
                proc.kill()
                proc.join(5)
        shutil.rmtree(workdir, ignore_errors=True)
