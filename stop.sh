#!/usr/bin/env bash
# Stops the pipeline (if running) and all containers. Volumes (Mongo, Ollama) are kept.
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"

docker exec arise_ergo_dckr bash -lc 'pkill -INT -f arise_ergo.launch.py' 2>/dev/null || true
sleep 5
docker compose --profile llm stop
