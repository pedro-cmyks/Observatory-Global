# Observatory Global - Development Runbook

## Quick Start (One Command)

```bash
./scripts/start-dev.sh
```

This starts: Database (Postgres) → Backend (:8000) → Frontend-v2 (:3000)

## Manual Start (Step by Step)

### 1. Database
```bash
docker-compose up -d postgres
```

### 2. Backend
```bash
cd backend
source ../.venv/bin/activate  # or backend/.venv/bin/activate
uvicorn app.main_v2:app --reload --port 8000
```

### 3. Frontend-v2 (REQUIRED - not legacy frontend/)
```bash
cd frontend-v2
npm install
npm run dev
```

### 4. Ingestion (Optional)
```bash
# One-time run
./scripts/start_ingestion.sh --once

# Continuous (every 15 min)
./scripts/start_ingestion.sh
```

---

## Verification Checklist

### Backend
```bash
curl -s http://localhost:8000/health | jq .
# Expected: {"status": "healthy", "db_ok": true, ...}

curl -s http://localhost:8000/api/indicators/tooltips | jq .
# Expected: {"source_diversity": "...", ...}
```

### Frontend
```bash
curl -s http://localhost:3000 | head -5
# Expected: HTML content
```

### Visual Checks
1. Open http://localhost:3000
2. Confirm green banner bottom-right: "frontend-v2 | :3000 → :8000 | MapLibre"
3. Map loads (no Mapbox watermark)
4. Click a country → side panel opens

---

## Troubleshooting

### "Port already in use"
```bash
./scripts/preflight.sh
# Follow instructions to kill conflicting process
```

### "Wrong UI showing"
- Check for green "frontend-v2" banner
- If missing, you may be running legacy frontend
- Stop all: `./scripts/stop-dev.sh`
- Restart: `./scripts/start-dev.sh`

### "Health shows degraded"
```bash
# Run ingestion
./scripts/start_ingestion.sh --once

# Check again
curl -s http://localhost:8000/health | jq .
```

---

## Ports Reference

| Service | Port | URL |
|---------|------|-----|
| Frontend-v2 | 3000 | http://localhost:3000 |
| Backend | 8000 | http://localhost:8000 |
| Postgres | 5432 | localhost:5432 |

---

## Stop Everything

```bash
./scripts/stop-dev.sh
```

---

## Weekend/Long-Running Ingestion

### Prerequisites
- Backend venv set up: `backend/.venv/`
- PostgreSQL running
- Sufficient disk space for logs

### Using the Ingestion Runner CLI

**IMPORTANT:** Always run from project root with the venv activated:

```bash
cd /Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal
source backend/.venv/bin/activate
```

**Start ingestion:**
```bash
python3 -m backend.app.services.ingest_runner start
```
This will:
- Start ingestion loop (every 15 min)
- Activate caffeinate (Mac won't sleep)
- Log to `logs/ingestion_YYYYMMDD_HHMM.log`
- Save PIDs to `.run/` for clean stop

**Check status:**
```bash
python3 -m backend.app.services.ingest_runner status
```

**Tail logs:**
```bash
python3 -m backend.app.services.ingest_runner tail
```

**Stop ingestion:**
```bash
python3 -m backend.app.services.ingest_runner stop
```

### Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ModuleNotFoundError: aiohttp` | Running outside venv | Run: `source backend/.venv/bin/activate` first |
| `python: command not found` | macOS uses python3 | Use `python3` not `python` |
| Ingestion stops silently | Mac went to sleep | The runner uses caffeinate automatically |
| "field larger than field limit" | Large GDELT fields | Fixed in V3.2 with 10MB limit |

### Manual One-Time Run (for testing)

```bash
source backend/.venv/bin/activate
python3 -m backend.app.services.ingest_v2
```


