#!/usr/bin/env python3
"""
Atlas Control Panel — Observatorio Global
Panel de control unificado. Sigue el orden del README:
  1. Docker  (PostgreSQL + Redis)
  2. Backend (FastAPI / uvicorn)
  3. Frontend (Vite / React)
  4. Ingesta  (GDELT, loop cada 15 min)

Uso:
    python atlas.py
"""

import os
import sys
import signal
import socket
import subprocess
import time
from pathlib import Path

# ── psutil ────────────────────────────────────────────────────────────────────
try:
    import psutil
except ImportError:
    print("\n[ERROR] psutil no está instalado.")
    print("  Instálalo con:  pip install psutil\n")
    sys.exit(1)

# ── Rutas ─────────────────────────────────────────────────────────────────────
ROOT         = Path(__file__).parent.resolve()
INFRA_DIR    = ROOT / "infra"
BACKEND_DIR  = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend-v2"
LOGS_DIR     = ROOT / "logs"
RUN_DIR      = ROOT / ".run"
ATLAS_DIR    = ROOT / ".atlas"

VENV_PYTHON  = BACKEND_DIR / ".venv" / "bin" / "python3"

BACKEND_PID_FILE  = ATLAS_DIR / "backend.pid"
FRONTEND_PID_FILE = ATLAS_DIR / "frontend.pid"
INGEST_PID_FILE   = ATLAS_DIR / "ingestion.pid"

DOCKER_CONTAINERS = ["observatory-postgres", "observatory-redis"]

# ── Colores ANSI ──────────────────────────────────────────────────────────────
GREEN  = "\033[0;32m"
RED    = "\033[0;31m"
YELLOW = "\033[1;33m"
CYAN   = "\033[0;36m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
NC     = "\033[0m"

def g(t): return f"{GREEN}{t}{NC}"
def r(t): return f"{RED}{t}{NC}"
def y(t): return f"{YELLOW}{t}{NC}"
def c(t): return f"{CYAN}{t}{NC}"
def b(t): return f"{BOLD}{t}{NC}"
def d(t): return f"{DIM}{t}{NC}"


# ── Helpers de red / proceso ──────────────────────────────────────────────────

def port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", port)) == 0


def port_pid(port: int) -> int | None:
    """PID del proceso en ese puerto vía lsof (sin privilegios especiales)."""
    if not port_open(port):
        return None
    try:
        out = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True, text=True,
        ).stdout.strip()
        pids = [int(p) for p in out.split("\n") if p.strip().isdigit()]
        return pids[0] if pids else None
    except Exception:
        return None


def pid_alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        psutil.Process(pid)
        return True
    except psutil.NoSuchProcess:
        return False


def read_pid(path: Path) -> int | None:
    try:
        if path.exists():
            return int(path.read_text().strip())
    except (ValueError, IOError):
        pass
    return None


def wait_port(port: int, timeout: int = 20) -> bool:
    for _ in range(timeout):
        if port_open(port):
            return True
        time.sleep(1)
    return False


def kill_pid(pid: int, label: str) -> bool:
    try:
        proc = psutil.Process(pid)
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except psutil.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=3)
        return True
    except psutil.NoSuchProcess:
        return True
    except Exception as e:
        print(f"\n    {r('ERROR')} deteniendo {label}: {e}")
        return False


def ensure_dirs():
    for d_ in (LOGS_DIR, RUN_DIR, ATLAS_DIR):
        d_.mkdir(parents=True, exist_ok=True)


# ── Docker ────────────────────────────────────────────────────────────────────

def docker_daemon_running() -> bool:
    """Retorna True si el daemon de Docker responde (Docker Desktop abierto)."""
    try:
        r = subprocess.run(
            ["docker", "info"],
            capture_output=True, timeout=5,
        )
        return r.returncode == 0
    except Exception:
        return False


def launch_docker_desktop():
    """Abre Docker Desktop en macOS y espera a que el daemon arranque."""
    print(f"  {c('→')} Abriendo Docker Desktop...", end=" ", flush=True)
    subprocess.Popen(["open", "-a", "Docker"])
    for _ in range(30):          # espera hasta 60 s
        time.sleep(2)
        if docker_daemon_running():
            print(g("listo"))
            return True
        print(".", end="", flush=True)
    print(f"\n  {r('ERROR')} Docker Desktop no arrancó a tiempo.")
    print(d("  Ábrelo manualmente y vuelve a correr atlas.py"))
    return False


def container_running(name: str) -> bool:
    try:
        out = subprocess.run(
            ["docker", "ps", "--filter", f"name={name}", "--format", "{{.Names}}"],
            capture_output=True, text=True, timeout=5,
        ).stdout.strip()
        return name in out
    except Exception:
        return False


def detect_docker() -> dict:
    daemon = docker_daemon_running()
    if not daemon:
        return {"available": True, "daemon": False, "running": False, "containers": {}}
    statuses = {name: container_running(name) for name in DOCKER_CONTAINERS}
    all_up = all(statuses.values())
    return {"available": True, "daemon": True, "running": all_up, "containers": statuses}


def start_docker(state: dict) -> bool:
    # Si el daemon no está corriendo, abrir Docker Desktop primero
    if not state.get("daemon", True):
        ok = launch_docker_desktop()
        if not ok:
            return False
        # Actualizar estado tras arrancar el daemon
        state = detect_docker()

    if state["running"]:
        print(f"  {y('─')} Docker           ya activo — sin cambios")
        return True

    print(f"  {c('→')} Iniciando contenedores (PostgreSQL + Redis)...", end=" ", flush=True)
    result = subprocess.run(
        ["docker", "compose", "up", "-d"],
        cwd=str(INFRA_DIR),
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(r("ERROR"))
        print(d(f"    {result.stderr.strip()[:200]}"))
        return False

    # Esperar a que los contenedores estén running
    for _ in range(20):
        time.sleep(1)
        if all(container_running(n) for n in DOCKER_CONTAINERS):
            break
    else:
        print(r("ERROR") + d("  contenedores no arrancaron"))
        return False

    # Esperar a que PostgreSQL acepte conexiones reales (no solo que el contenedor exista)
    print(f"\n  {c('→')} Esperando a que PostgreSQL acepte conexiones...", end=" ", flush=True)
    for _ in range(30):
        if port_open(5432):
            print(g("listo") + d("  postgres:5432  redis:6379"))
            return True
        time.sleep(1)
        print(".", end="", flush=True)
    print(r("\n  ERROR") + d("  PostgreSQL no respondió a tiempo"))
    return False

    print(y("iniciando…") + d("  pueden tardar unos segundos más"))
    return True


def stop_docker(state: dict) -> bool:
    if not state["available"] or not state["running"]:
        print(f"  {y('─')} Docker           ya inactivo — sin cambios")
        return True

    print(f"  {r('→')} Deteniendo Docker...", end=" ", flush=True)
    result = subprocess.run(
        ["docker", "compose", "stop"],
        cwd=str(INFRA_DIR),
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        print(g("DETENIDO"))
        return True
    print(r("ERROR") + d(f"  {result.stderr.strip()[:120]}"))
    return False


# ── Detección de servicios locales ────────────────────────────────────────────

def detect_backend() -> dict:
    pid = port_pid(8000)
    return {"running": pid is not None, "pid": pid, "port": 8000}


def detect_frontend() -> dict:
    pid = port_pid(3000)
    return {"running": pid is not None, "pid": pid, "port": 3000}


def detect_ingestion() -> dict:
    pid = read_pid(INGEST_PID_FILE)
    alive = pid_alive(pid)
    if pid and not alive:
        INGEST_PID_FILE.unlink(missing_ok=True)
        pid = None
    return {"running": alive, "pid": pid}


# ── Banner y estado ───────────────────────────────────────────────────────────

def print_banner():
    print()
    print(f"{CYAN}{BOLD}  ╔══════════════════════════════════════════╗{NC}")
    print(f"{CYAN}{BOLD}  ║       ATLAS Control Panel                ║{NC}")
    print(f"{CYAN}{BOLD}  ║       Observatorio Global                ║{NC}")
    print(f"{CYAN}{BOLD}  ╚══════════════════════════════════════════╝{NC}")
    print()


def _status_row(label: str, running: bool, extra: str = "") -> str:
    dot   = g("●") if running else r("○")
    state = g("ACTIVO") if running else r("INACTIVO")
    tail  = ("  " + d(extra)) if extra and running else ""
    return f"  {dot} {label:<24} {state}{tail}"


def print_state(docker: dict, backend: dict, frontend: dict, ingestion: dict):
    print(b("  Estado actual:"))

    if not docker.get("daemon", True):
        print(f"  {y('○')} {'Docker Desktop':<24} {y('CERRADO')}  {d('se abrirá automáticamente')}")
    elif docker["containers"]:
        for name, up in docker["containers"].items():
            short = name.replace("observatory-", "")
            print(_status_row(f"Docker / {short}", up))
    else:
        print(f"  {r('○')} {'Docker':<24} {r('NO DISPONIBLE')}")

    print(_status_row("Backend   (FastAPI)", backend["running"], "http://localhost:8000"))
    print(_status_row("Frontend  (Vite)",   frontend["running"], "http://localhost:3000"))
    print(_status_row("Ingesta   (GDELT)",  ingestion["running"], "ciclos cada 15 min"))
    print()


# ── Menú ──────────────────────────────────────────────────────────────────────

def ask_action() -> str:
    print(b("  ¿Qué deseas hacer?"))
    print(f"    {g('[1]')} Encender todos los servicios")
    print(f"    {r('[2]')} Apagar todos los servicios")
    print(f"    {y('[q]')} Salir")
    print()
    try:
        return input("  > ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return "q"


# ── Encender ──────────────────────────────────────────────────────────────────

def start_backend(state: dict) -> bool:
    if state["running"]:
        print(f"  {y('─')} Backend          ya activo — sin cambios")
        return True

    ensure_dirs()
    log = LOGS_DIR / "backend.log"
    python_bin = str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable

    print(f"  {c('→')} Iniciando Backend...", end=" ", flush=True)
    with open(log, "a") as lf:
        proc = subprocess.Popen(
            [python_bin, "-m", "uvicorn", "app.main_v2:app",
             "--reload", "--host", "0.0.0.0", "--port", "8000"],
            cwd=str(BACKEND_DIR),
            stdout=lf, stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    BACKEND_PID_FILE.write_text(str(proc.pid))

    if wait_port(8000, timeout=15):
        print(g("OK") + d(f"  PID {proc.pid}  http://localhost:8000"))
        return True
    if pid_alive(proc.pid):
        print(y("iniciando…") + d("  revisa logs/backend.log"))
        return True
    print(r("ERROR") + d("  proceso terminó — revisa logs/backend.log"))
    return False


def start_frontend(state: dict) -> bool:
    if state["running"]:
        print(f"  {y('─')} Frontend         ya activo — sin cambios")
        return True

    ensure_dirs()
    log = LOGS_DIR / "frontend.log"

    if not (FRONTEND_DIR / "node_modules").exists():
        print(f"  {c('→')} npm install...", end=" ", flush=True)
        res = subprocess.run(["npm", "install"], cwd=str(FRONTEND_DIR), capture_output=True)
        if res.returncode != 0:
            print(r("ERROR") + " npm install falló")
            return False
        print(g("OK"))

    print(f"  {c('→')} Iniciando Frontend...", end=" ", flush=True)
    with open(log, "a") as lf:
        proc = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=str(FRONTEND_DIR),
            stdout=lf, stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    FRONTEND_PID_FILE.write_text(str(proc.pid))

    if wait_port(3000, timeout=20):
        print(g("OK") + d(f"  PID {proc.pid}  http://localhost:3000"))
        return True
    if pid_alive(proc.pid):
        print(y("iniciando…") + d("  revisa logs/frontend.log"))
        return True
    print(r("ERROR") + d("  proceso terminó — revisa logs/frontend.log"))
    return False


def start_ingestion(state: dict) -> bool:
    if state["running"]:
        print(f"  {y('─')} Ingesta GDELT    ya activo — sin cambios")
        return True

    ensure_dirs()
    log = LOGS_DIR / "ingestion.log"
    python_bin = str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable

    # Mismo patrón que auto_ingest_v2.sh: ejecutar ingest_v2 en loop cada 15 min
    loop_script = (
        "import asyncio, sys\n"
        "from datetime import datetime\n"
        "sys.path.insert(0, '.')\n"
        "async def loop():\n"
        "    from app.services.ingest_v2 import run_ingestion\n"
        "    while True:\n"
        "        print(f'[{datetime.now():%Y-%m-%d %H:%M:%S}] ciclo iniciado', flush=True)\n"
        "        try:\n"
        "            await run_ingestion()\n"
        "            print(f'[{datetime.now():%Y-%m-%d %H:%M:%S}] ciclo completo. Durmiendo 15 min...', flush=True)\n"
        "        except Exception as e:\n"
        "            print(f'[{datetime.now():%Y-%m-%d %H:%M:%S}] ERROR: {e}', flush=True)\n"
        "            await asyncio.sleep(60)\n"
        "            continue\n"
        "        await asyncio.sleep(900)\n"
        "asyncio.run(loop())\n"
    )

    print(f"  {c('→')} Iniciando Ingesta GDELT...", end=" ", flush=True)
    with open(log, "a") as lf:
        proc = subprocess.Popen(
            [python_bin, "-c", loop_script],
            cwd=str(BACKEND_DIR),
            stdout=lf, stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    INGEST_PID_FILE.write_text(str(proc.pid))
    time.sleep(3)

    if pid_alive(proc.pid):
        print(g("OK") + d(f"  PID {proc.pid}  (ciclos cada 15 min)"))
        return True
    INGEST_PID_FILE.unlink(missing_ok=True)
    print(r("ERROR") + d("  proceso terminó — revisa logs/ingestion.log"))
    return False


def action_encender(docker: dict, backend: dict, frontend: dict, ingestion: dict):
    print()
    print(b("  Encendiendo Atlas..."))
    print()

    ok_d = start_docker(docker)
    if not ok_d:
        print(f"\n  {r('✗')} Docker falló — abortando (backend y frontend necesitan la DB)")
        return

    ok_b = start_backend(backend)
    ok_f = start_frontend(frontend)
    ok_i = start_ingestion(ingestion)

    print()
    print(b("  Resumen:"))
    for label, ok, url in [
        ("Docker (pg + redis)", ok_d, "localhost:5432 / 6379"),
        ("Backend  (FastAPI)", ok_b, "http://localhost:8000"),
        ("Frontend (Vite)",   ok_f, "http://localhost:3000"),
        ("Ingesta  (GDELT)",  ok_i, "logs/ingestion.log"),
    ]:
        if ok:
            print(f"  {g('✓')} {label:<22}  {g('OK')}  {d(url)}")
        else:
            print(f"  {r('✗')} {label:<22}  {r('ERROR')}  {d('revisa los logs')}")


# ── Apagar ────────────────────────────────────────────────────────────────────

def stop_process(pid_file: Path, port: int | None, label: str, use_pgid: bool = False) -> bool:
    # Buscar PID: primero pid file, luego por puerto
    pid = read_pid(pid_file)
    if not pid and port:
        pid = port_pid(port)
    if not pid:
        print(f"  {y('─')} {label:<22} ya inactivo — sin cambios")
        return True

    print(f"  {r('→')} Deteniendo {label} (PID {pid})...", end=" ", flush=True)
    ok = True
    if use_pgid:
        try:
            pgid = os.getpgid(pid)
            os.killpg(pgid, signal.SIGTERM)
            time.sleep(3)
            try:
                os.killpg(pgid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        except Exception:
            ok = kill_pid(pid, label)
    else:
        ok = kill_pid(pid, label)

    pid_file.unlink(missing_ok=True)
    print(g("DETENIDO") if ok else r("ERROR"))
    return ok


def action_apagar(docker: dict, **_):
    print()
    print(b("  Apagando Atlas..."))
    print()

    # Apagar en orden inverso: ingesta → frontend → backend → docker
    ok_i = stop_process(INGEST_PID_FILE,  None, "Ingesta  (GDELT)")
    ok_f = stop_process(FRONTEND_PID_FILE, 3000, "Frontend (Vite)", use_pgid=True)
    ok_b = stop_process(BACKEND_PID_FILE,  8000, "Backend  (FastAPI)")
    ok_d = stop_docker(docker)

    print()
    print(b("  Resumen:"))
    for label, ok in [
        ("Ingesta  (GDELT)",  ok_i),
        ("Frontend (Vite)",   ok_f),
        ("Backend  (FastAPI)", ok_b),
        ("Docker (pg + redis)", ok_d),
    ]:
        marker = g("✓ DETENIDO") if ok else r("✗ ERROR")
        print(f"  {marker}  {label}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print_banner()

    docker    = detect_docker()
    backend   = detect_backend()
    frontend  = detect_frontend()
    ingestion = detect_ingestion()

    print_state(docker, backend, frontend, ingestion)

    choice = ask_action()

    if choice in ("1", "e", "encender"):
        action_encender(docker, backend, frontend, ingestion)
    elif choice in ("2", "a", "apagar"):
        action_apagar(docker, backend, frontend, ingestion)
    elif choice in ("q", ""):
        print(d("  Saliendo."))
    else:
        print(y(f"  Opción no reconocida: '{choice}'  (usa 1, 2 o q)"))

    print()


if __name__ == "__main__":
    main()
