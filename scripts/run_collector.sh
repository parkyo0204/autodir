#!/usr/bin/env bash
set -u -o pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${HOME}/.config/autodir/env"
LOG_DIR="${PROJECT_DIR}/logs"
LOG_FILE="${LOG_DIR}/cron.log"

umask 077
mkdir -p "$LOG_DIR"
touch "$LOG_FILE"
chmod 600 "$LOG_FILE"

if [[ ! -r "$ENV_FILE" ]]; then
    printf '[%s] missing environment file: %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$ENV_FILE" >&2
    exit 1
fi

source "$ENV_FILE"
started_at="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
printf '\n[%s] collector start\n' "$started_at" >> "$LOG_FILE"

"${PROJECT_DIR}/venv/bin/python" "${PROJECT_DIR}/scripts/run_pipeline.py" --skip-reddit >> "$LOG_FILE" 2>&1
status=$?

printf '[%s] collector exit=%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$status" >> "$LOG_FILE"
exit "$status"
