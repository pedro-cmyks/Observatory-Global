#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

fly deploy \
  --config fly.toml \
  --build-target nlp-runtime \
  --process-groups nlp_worker \
  "$@"
