#!/usr/bin/env python3
"""
Ingestion Runner CLI for Observatory Global.

Usage:
    python3 -m backend.app.services.ingest_runner start
    python3 -m backend.app.services.ingest_runner stop
    python3 -m backend.app.services.ingest_runner status
    python3 -m backend.app.services.ingest_runner tail

This module handles:
- Starting ingestion in background with caffeinate (macOS sleep prevention)
- PID file management for clean stop
- Log rotation with timestamped files
"""
import os
import sys
import signal
import subprocess
import time
from datetime import datetime
from pathlib import Path

# Directories
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent  # backend/app/services -> project root
LOGS_DIR = PROJECT_ROOT / "logs"
RUN_DIR = PROJECT_ROOT / ".run"

# PID files
INGEST_PID_FILE = RUN_DIR / "ingest_v2.pid"
CAFFEINATE_PID_FILE = RUN_DIR / "caffeinate.pid"

# Venv python path
VENV_PYTHON = PROJECT_ROOT / "backend" / ".venv" / "bin" / "python3"


def get_log_file() -> Path:
    """Get current log file path (latest or new)."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    # Find latest log file or create new one
    existing = sorted(LOGS_DIR.glob("ingestion_*.log"), reverse=True)
    if existing:
        return existing[0]
    return LOGS_DIR / f"ingestion_{datetime.now().strftime('%Y%m%d_%H%M')}.log"


def new_log_file() -> Path:
    """Create a new timestamped log file path."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    return LOGS_DIR / f"ingestion_{datetime.now().strftime('%Y%m%d_%H%M')}.log"


def read_pid(pid_file: Path) -> int | None:
    """Read PID from file, return None if not exists or invalid."""
    try:
        if pid_file.exists():
            pid = int(pid_file.read_text().strip())
            return pid
    except (ValueError, IOError):
        pass
    return None


def is_pid_running(pid: int) -> bool:
    """Check if a PID is running."""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def start():
    """Start ingestion with caffeinate."""
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    
    # Check if already running
    ingest_pid = read_pid(INGEST_PID_FILE)
    if ingest_pid and is_pid_running(ingest_pid):
        print(f"❌ Ingestion already running (PID {ingest_pid})")
        print("   Run 'stop' first or check 'status'")
        return
    
    # Verify venv python exists
    if not VENV_PYTHON.exists():
        print(f"❌ Venv python not found: {VENV_PYTHON}")
        print("   Run: cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -e .")
        return
    
    log_file = new_log_file()
    print(f"📁 Log file: {log_file}")
    
    # Ingestion script path (relative to backend directory)
    backend_dir = PROJECT_ROOT / "backend"
    
    # Start ingestion process
    # Run from backend/ directory so relative imports work (from app.config...)
    # Use a loop since ingest_v2.run_ingestion() does one fetch and exits
    ingest_script = '''
import asyncio
import sys
import time
from datetime import datetime

async def run_loop():
    from app.services.ingest_v2 import run_ingestion
    
    print(f"[{datetime.now()}] Ingestion loop started", flush=True)
    while True:
        try:
            await run_ingestion()
            print(f"[{datetime.now()}] Cycle complete. Sleeping 15 minutes...", flush=True)
        except Exception as e:
            print(f"[{datetime.now()}] Ingestion error: {e}", flush=True)
            import traceback
            traceback.print_exc()
            print("Sleeping 60s before retry...", flush=True)
            await asyncio.sleep(60)
            continue
        await asyncio.sleep(900)  # 15 minutes

asyncio.run(run_loop())
'''
    
    ingest_cmd = [str(VENV_PYTHON), "-c", ingest_script]
    
    with open(log_file, 'a') as log:
        log.write(f"\n{'='*60}\n")
        log.write(f"Ingestion started at {datetime.now().isoformat()}\n")
        log.write(f"Python: {VENV_PYTHON}\n")
        log.write(f"CWD: {backend_dir}\n")
        log.write(f"{'='*60}\n\n")
        log.flush()
        
        ingest_proc = subprocess.Popen(
            ingest_cmd,
            stdout=log,
            stderr=subprocess.STDOUT,
            cwd=str(backend_dir),  # Run from backend/ so relative imports work
            start_new_session=True
        )
    
    # Save ingestion PID
    INGEST_PID_FILE.write_text(str(ingest_proc.pid))
    print(f"✅ Ingestion started (PID {ingest_proc.pid})")
    
    # Start caffeinate to keep Mac awake while ingestion runs
    try:
        caffeinate_proc = subprocess.Popen(
            ["caffeinate", "-dims", "-w", str(ingest_proc.pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        CAFFEINATE_PID_FILE.write_text(str(caffeinate_proc.pid))
        print(f"☕ Caffeinate started (PID {caffeinate_proc.pid}) - Mac will stay awake")
    except FileNotFoundError:
        print("⚠️  caffeinate not found - Mac may sleep (not on macOS?)")
    
    print(f"\n📊 Monitor with: python3 -m backend.app.services.ingest_runner tail")
    print(f"🛑 Stop with:    python3 -m backend.app.services.ingest_runner stop")


def stop():
    """Stop ingestion gracefully."""
    stopped_any = False
    
    # Stop ingestion
    ingest_pid = read_pid(INGEST_PID_FILE)
    if ingest_pid:
        if is_pid_running(ingest_pid):
            print(f"🛑 Stopping ingestion (PID {ingest_pid})...")
            try:
                os.kill(ingest_pid, signal.SIGTERM)
                # Wait up to 5 seconds for graceful stop
                for _ in range(10):
                    if not is_pid_running(ingest_pid):
                        break
                    time.sleep(0.5)
                else:
                    # Force kill if still running
                    os.kill(ingest_pid, signal.SIGKILL)
                print("   ✅ Ingestion stopped")
                stopped_any = True
            except ProcessLookupError:
                print("   Already stopped")
        INGEST_PID_FILE.unlink(missing_ok=True)
    
    # Stop caffeinate
    caff_pid = read_pid(CAFFEINATE_PID_FILE)
    if caff_pid:
        if is_pid_running(caff_pid):
            try:
                os.kill(caff_pid, signal.SIGTERM)
                print("☕ Caffeinate stopped")
                stopped_any = True
            except ProcessLookupError:
                pass
        CAFFEINATE_PID_FILE.unlink(missing_ok=True)
    
    if not stopped_any:
        print("ℹ️  Nothing was running")
    
    # Also kill any orphaned ingestion processes
    try:
        result = subprocess.run(
            ["pkill", "-f", "ingest_v2"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print("🧹 Cleaned up orphaned ingestion processes")
    except FileNotFoundError:
        pass


def status():
    """Show ingestion status."""
    print("=" * 50)
    print("INGESTION STATUS")
    print("=" * 50)
    
    # Check ingestion
    ingest_pid = read_pid(INGEST_PID_FILE)
    if ingest_pid and is_pid_running(ingest_pid):
        print(f"✅ Ingestion:   RUNNING (PID {ingest_pid})")
    elif ingest_pid:
        print(f"❌ Ingestion:   STOPPED (stale PID {ingest_pid})")
        INGEST_PID_FILE.unlink(missing_ok=True)
    else:
        print("⭕ Ingestion:   NOT RUNNING")
    
    # Check caffeinate
    caff_pid = read_pid(CAFFEINATE_PID_FILE)
    if caff_pid and is_pid_running(caff_pid):
        print(f"☕ Caffeinate:  RUNNING (PID {caff_pid})")
    else:
        print("⭕ Caffeinate:  NOT RUNNING")
    
    # Show log info
    log_file = get_log_file()
    if log_file.exists():
        size_kb = log_file.stat().st_size / 1024
        print(f"\n📁 Log file:    {log_file}")
        print(f"   Size:        {size_kb:.1f} KB")
        print("\n--- Last 15 lines ---")
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()[-15:]
                for line in lines:
                    print(f"   {line.rstrip()}")
        except IOError:
            print("   (could not read log)")
    else:
        print("\n📁 No log files found")
    
    print("=" * 50)


def tail():
    """Tail the current log file."""
    log_file = get_log_file()
    if not log_file.exists():
        print(f"❌ No log file found in {LOGS_DIR}")
        return
    
    print(f"📁 Tailing: {log_file}")
    print("   Press Ctrl+C to stop\n")
    try:
        subprocess.run(["tail", "-f", str(log_file)])
    except KeyboardInterrupt:
        print("\n👋 Stopped tailing")


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 -m backend.app.services.ingest_runner <command>")
        print("")
        print("Commands:")
        print("  start   Start ingestion in background (with caffeinate)")
        print("  stop    Stop ingestion gracefully")
        print("  status  Show current status and recent logs")
        print("  tail    Tail the current log file")
        return
    
    cmd = sys.argv[1].lower()
    
    if cmd == "start":
        start()
    elif cmd == "stop":
        stop()
    elif cmd == "status":
        status()
    elif cmd == "tail":
        tail()
    else:
        print(f"Unknown command: {cmd}")
        print("Valid commands: start, stop, status, tail")


if __name__ == "__main__":
    main()
