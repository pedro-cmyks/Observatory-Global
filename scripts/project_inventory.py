#!/usr/bin/env python3
"""Project inventory — single source of truth for who-touches-what.

Emits `docs/state/PROJECT_INVENTORY.md` with a machine-verified map of:

  - Endpoints (backend/app/routers/*.py)
  - Frontend ↔ API callsites (frontend-v2/src/**)
  - DB tables (backend/migrations/*.sql), cross-referenced with router reads
  - Cron jobs (`~/Library/LaunchAgents/com.atlas.*.plist`) + last log mtime
  - Recent commits (last 2 weeks)

Designed to be re-run every session start (or before opening a thorny
multi-file task). Stdlib only — no extra deps.

Regen:
  python scripts/project_inventory.py
"""
from __future__ import annotations

import plistlib
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ROUTERS_DIR = REPO / "backend" / "app" / "routers"
MIGRATIONS_DIR = REPO / "backend" / "migrations"
FRONTEND_DIR = REPO / "frontend-v2" / "src"
LAUNCHAGENTS = Path.home() / "Library" / "LaunchAgents"
OUT = REPO / "docs" / "state" / "PROJECT_INVENTORY.md"

ROUTE_RE = re.compile(r"@router\.(get|post|put|delete|patch)\(\s*[\"']([^\"']+)[\"']")
PREFIX_RE = re.compile(r"APIRouter\([^)]*prefix\s*=\s*[\"']([^\"']+)[\"']")
FUNC_RE = re.compile(r"(?:async\s+)?def\s+(\w+)\s*\(")
# Case-sensitive: SQL embedded in Python uses uppercase keywords. This
# prevents capturing Python `from X import Y` imports as table names.
TABLE_FROM_RE = re.compile(r"\bFROM\s+([a-z_][a-z0-9_]*)")
TABLE_JOIN_RE = re.compile(r"\bJOIN\s+([a-z_][a-z0-9_]*)")
TABLE_INTO_RE = re.compile(r"\bINSERT\s+INTO\s+([a-z_][a-z0-9_]*)")
TABLE_UPDATE_RE = re.compile(r"\bUPDATE\s+([a-z_][a-z0-9_]*)")
CREATE_TABLE_RE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)", re.IGNORECASE
)
# Frontend api callsites — accept ', ", or backtick (templated URLs).
# Path matches up to first non-URL char (?, ', ", `, space, newline).
API_CALL_RE = re.compile(r"['\"`](/api/v[12]/[a-zA-Z0-9_/\-{}]*)")

# Common CTE/subquery aliases + Python keywords that slip through when
# SQL keywords accidentally land lowercase. The case-sensitive regex
# already eliminates most of these; the list is a belt-and-suspenders.
NOISE_TABLES = {
    "path", "self", "where", "select", "as", "on", "now", "exists",
    "app", "fastapi", "the", "exc", "recent", "pre", "nodes",
    "filtered", "ranked", "matches", "totals", "live", "pg_class",
    "information_schema", "array", "materialized", "unnest", "agg",
    "datetime", "baseline", "baseline_data", "current_period",
    "current_window", "daily_history", "theme", "theme_counts",
}


def _prefix_for(src: str) -> str:
    m = PREFIX_RE.search(src)
    return m.group(1) if m else ""


def _tables_in_block(text: str) -> list[str]:
    found: set[str] = set()
    for rx in (TABLE_FROM_RE, TABLE_JOIN_RE, TABLE_INTO_RE, TABLE_UPDATE_RE):
        for m in rx.finditer(text):
            name = m.group(1).lower()
            if name in NOISE_TABLES or len(name) <= 2:
                continue
            found.add(name)
    return sorted(found)


def scan_endpoints() -> list[dict]:
    routes: list[dict] = []
    for f in sorted(ROUTERS_DIR.glob("*.py")):
        if f.name == "__init__.py":
            continue
        src = f.read_text(encoding="utf-8", errors="replace")
        prefix = _prefix_for(src)
        for m in ROUTE_RE.finditer(src):
            method = m.group(1).upper()
            raw_path = m.group(2)
            full_path = (prefix + raw_path) if prefix and not raw_path.startswith("/api") else raw_path
            if prefix and raw_path.startswith("/") and not raw_path.startswith(prefix):
                full_path = prefix + raw_path
            tail = src[m.end():]
            func_m = FUNC_RE.search(tail)
            func = func_m.group(1) if func_m else "?"
            # body block ≈ 80 lines after the route decorator (heuristic)
            body = "\n".join(tail.split("\n")[:80])
            routes.append({
                "method": method,
                "path": full_path,
                "file": str(f.relative_to(REPO)),
                "func": func,
                "tables": _tables_in_block(body),
            })
    return routes


def scan_frontend_api_calls() -> dict[str, list[str]]:
    mapping: dict[str, set[str]] = {}
    for ext in ("*.tsx", "*.ts"):
        for f in FRONTEND_DIR.rglob(ext):
            try:
                src = f.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for m in API_CALL_RE.finditer(src):
                path = m.group(1).split("?")[0]
                mapping.setdefault(path, set()).add(str(f.relative_to(REPO)))
    return {k: sorted(v) for k, v in mapping.items()}


def scan_migrations() -> dict[str, str]:
    tables: dict[str, str] = {}
    for f in sorted(MIGRATIONS_DIR.glob("*.sql")):
        src = f.read_text(encoding="utf-8", errors="replace")
        for m in CREATE_TABLE_RE.finditer(src):
            tables.setdefault(m.group(1).lower(), str(f.relative_to(REPO)))
    return tables


def _tail_last_line(path: Path) -> str:
    try:
        with open(path, "rb") as fh:
            fh.seek(0, 2)
            end = fh.tell()
            fh.seek(max(end - 4000, 0))
            chunk = fh.read().decode("utf-8", errors="replace")
        lines = [l for l in chunk.split("\n") if l.strip()]
        return lines[-1] if lines else ""
    except OSError:
        return ""


def scan_cron() -> list[dict]:
    jobs: list[dict] = []
    if not LAUNCHAGENTS.is_dir():
        return jobs
    for plist in sorted(LAUNCHAGENTS.glob("com.atlas.*.plist")):
        try:
            data = plistlib.loads(plist.read_bytes())
        except Exception:
            continue
        label = data.get("Label", plist.stem)
        program_args = data.get("ProgramArguments") or []
        program = program_args[0] if program_args else None
        intervals = data.get("StartCalendarInterval") or data.get("StartInterval")
        run_at_load = bool(data.get("RunAtLoad", False))
        log_out = data.get("StandardOutPath")
        log_err = data.get("StandardErrorPath")
        last_mtime = None
        last_line = ""
        for log_path in (log_out, log_err):
            if not log_path:
                continue
            p = Path(log_path)
            if not p.is_file():
                continue
            try:
                mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
            except OSError:
                continue
            if last_mtime is None or mtime > last_mtime:
                last_mtime = mtime
                last_line = _tail_last_line(p)
        status = ""
        try:
            r = subprocess.run(
                ["launchctl", "list", label],
                check=False, capture_output=True, text=True, timeout=5,
            )
            if r.returncode == 0:
                first = r.stdout.splitlines()[0] if r.stdout else ""
                status = first[:80]
        except Exception:
            pass
        jobs.append({
            "label": label,
            "program": program,
            "intervals": intervals,
            "run_at_load": run_at_load,
            "log_mtime": last_mtime.isoformat() if last_mtime else None,
            "log_last_line": last_line[:160],
            "status": status,
        })
    return jobs


def recent_commits(weeks: int = 2) -> list[str]:
    try:
        r = subprocess.run(
            [
                "git", "log",
                f"--since={weeks}.weeks",
                "--pretty=format:%h %ad %s",
                "--date=short",
            ],
            check=True, capture_output=True, text=True, cwd=REPO,
        )
        return [line for line in r.stdout.split("\n") if line.strip()]
    except Exception:
        return []


def _fmt_schedule(intervals) -> str:
    if isinstance(intervals, list):
        return ", ".join(
            f"{i.get('Hour', '*')}:{int(i.get('Minute', 0)):02d}"
            for i in intervals
        )
    if isinstance(intervals, int):
        return f"every {intervals}s"
    return "—"


def render(
    endpoints: list[dict],
    fe_map: dict[str, list[str]],
    migrations: dict[str, str],
    cron: list[dict],
    commits: list[str],
) -> str:
    lines: list[str] = []
    lines.append("# Project Inventory")
    lines.append("")
    lines.append(f"Generated: {datetime.now(timezone.utc).isoformat()}  ")
    lines.append("Regen: `python scripts/project_inventory.py`")
    lines.append("")

    lines.append("## Endpoints (backend)")
    lines.append("")
    lines.append("| Method | Path | Router | Function | Tables touched |")
    lines.append("|---|---|---|---|---|")
    for r in sorted(endpoints, key=lambda r: (r["path"], r["method"])):
        tables = ", ".join(f"`{t}`" for t in r["tables"]) if r["tables"] else "—"
        lines.append(
            f"| {r['method']} | `{r['path']}` | `{r['file']}` | "
            f"`{r['func']}` | {tables} |"
        )
    lines.append("")

    lines.append("## Frontend → API map")
    lines.append("")
    lines.append("Where `/api/...` is called from. Multiple callers = shared surface.")
    lines.append("")
    lines.append("| Endpoint | Frontend file(s) |")
    lines.append("|---|---|")
    for path in sorted(fe_map.keys()):
        files = "<br/>".join(f"`{f}`" for f in fe_map[path])
        lines.append(f"| `{path}` | {files} |")
    lines.append("")

    lines.append("## DB tables (from migrations)")
    lines.append("")
    lines.append("| Table | Created by | Read by (router) |")
    lines.append("|---|---|---|")
    table_readers: dict[str, set[str]] = {}
    for r in endpoints:
        for t in r["tables"]:
            table_readers.setdefault(t, set()).add(r["file"])
    for table in sorted(migrations.keys()):
        readers = sorted(table_readers.get(table, set()))
        readers_str = "<br/>".join(f"`{x}`" for x in readers) if readers else "—"
        lines.append(f"| `{table}` | `{migrations[table]}` | {readers_str} |")
    lines.append("")

    lines.append("## Cron jobs (launchd)")
    lines.append("")
    if not cron:
        lines.append("_No `com.atlas.*` plists in `~/Library/LaunchAgents`._")
    else:
        lines.append(
            "| Label | Program | Schedule | RunAtLoad | "
            "Last log mtime | Last log line |"
        )
        lines.append("|---|---|---|---|---|---|")
        for j in cron:
            last = (j["log_last_line"] or "").replace("|", "\\|")[:140]
            lines.append(
                f"| `{j['label']}` | `{j['program']}` | {_fmt_schedule(j['intervals'])} | "
                f"{j['run_at_load']} | {j['log_mtime'] or '—'} | {last} |"
            )
    lines.append("")

    lines.append("## Recent commits (last 2 weeks)")
    lines.append("")
    for c in commits[:80]:
        lines.append(f"- `{c}`")
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    endpoints = scan_endpoints()
    fe_map = scan_frontend_api_calls()
    migrations = scan_migrations()
    cron = scan_cron()
    commits = recent_commits()
    text = render(endpoints, fe_map, migrations, cron, commits)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT.relative_to(REPO)}")
    print(f"  endpoints:        {len(endpoints)}")
    print(f"  frontend paths:   {len(fe_map)}")
    print(f"  migration tables: {len(migrations)}")
    print(f"  cron jobs:        {len(cron)}")
    print(f"  recent commits:   {len(commits)}")


if __name__ == "__main__":
    main()
