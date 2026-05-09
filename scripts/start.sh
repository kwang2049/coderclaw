#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${ROOT_DIR}/.venv"
ENV_FILE="${ROOT_DIR}/.env"
STATE_DIR="${ROOT_DIR}/.coderclaw"
LOG_DIR="${STATE_DIR}/logs"
TIMESTAMP="$(date +"%Y%m%dT%H%M%S")"
LOG_FILE="${LOG_DIR}/coderclaw-${TIMESTAMP}.log"

if [[ ! -x "${VENV_DIR}/bin/coderclaw" ]]; then
  echo "CoderClaw is not installed yet. Run scripts/install.sh first." >&2
  exit 1
fi

if [[ -f "${ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
fi

HOST="${CODERCLAW_HOST:-127.0.0.1}"
PORT="${CODERCLAW_PORT:-8787}"
EXISTING_PID="$(lsof -tiTCP:${PORT} -sTCP:LISTEN 2>/dev/null | head -n 1 || true)"

if [[ -n "${EXISTING_PID}" ]]; then
  echo "CoderClaw appears to already be running on ${HOST}:${PORT} (PID ${EXISTING_PID})."
  read -r -p "Kill the existing process and restart? [y/N] " REPLY
  if [[ "${REPLY}" =~ ^[Yy]$ ]]; then
    kill "${EXISTING_PID}"
    echo "Stopped PID ${EXISTING_PID}"
  else
    echo "Leaving the existing process running; start aborted."
    exit 0
  fi
fi

cd "${ROOT_DIR}"
mkdir -p "${LOG_DIR}"
export PYTHONPATH="${ROOT_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"
nohup "${VENV_DIR}/bin/coderclaw" >> "${LOG_FILE}" 2>&1 &
NEW_PID="$!"
echo "CoderClaw started in background on ${HOST}:${PORT} (PID ${NEW_PID})"
echo "Log file: ${LOG_FILE}"
