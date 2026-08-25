#!/bin/bash
# Stage-B SEMANAL del archivo (R1 del plan archivo-al-frente, 2026-08-25).
#
# Por qué existe: archive_story_units se congeló el 2026-07-03 porque el
# pipeline solo corrió UNA vez a mano y nadie lo notó durante 7.5 semanas
# (el endpoint deep-history respondía "bonito" con historia muerta — M0.2).
# Este runner lo vuelve semanal: embed incremental del archivo (OpenAI
# 3-small, resumable por manifest, centavos/semana) → repartition
# incremental por-shard → cluster HDBSCAN por día (resumable, nice) →
# load idempotente a archive_story_units.
#
# Todo resumible: una corrida matada continúa la siguiente semana.
# Non-fatal por paso NO: aquí cada paso alimenta al siguiente — un fallo
# corta y sale non-cero para que launchd lo registre (la lección L1: un
# runner que "exit 0" con pasos muertos es invisible).
set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"
export LC_ALL=en_US.UTF-8

ALW="/Users/pedro/AtlasLocalWorker"
REPO="${ATLAS_REPO_DIR:-/Users/pedro/ObservatorioGlobal}"
MLPY="${ATLAS_MLVENV:-$ALW/mlvenv}/bin/python"
EXT="/Volumes/Ext/Atlas"

# El archivo vive en el volumen externo — sin volumen no hay Stage-B.
if [[ ! -d "$EXT/Archive" ]]; then
  echo "[stage-b] /Volumes/Ext no montado — skip" >&2
  exit 2
fi

set -a; source "$ALW/.env"; set +a
cd "$REPO"

echo "[stage-b] weekly run start $(date '+%F %T')" >&2
taskpolicy -b "$MLPY" backend/scripts/archive_embed_pipeline.py \
  || { echo "[stage-b] embed FAILED" >&2; exit 1; }
taskpolicy -b "$MLPY" backend/scripts/archive_story_units.py repartition \
  || { echo "[stage-b] repartition FAILED" >&2; exit 1; }
taskpolicy -b "$MLPY" backend/scripts/archive_story_units.py cluster --jobs 2 \
  || { echo "[stage-b] cluster FAILED" >&2; exit 1; }
"$MLPY" backend/scripts/load_archive_units.py --write \
  || { echo "[stage-b] load FAILED" >&2; exit 1; }
echo "[stage-b] weekly run DONE $(date '+%F %T')" >&2
