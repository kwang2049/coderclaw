#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${ROOT_DIR}/.venv"
ENV_FILE="${ROOT_DIR}/.env"
ENV_EXAMPLE="${ROOT_DIR}/.env.example"

if ! command -v python >/dev/null 2>&1; then
  echo "python is required but was not found in PATH" >&2
  exit 1
fi

PYTHON_VERSION="$(python --version 2>&1)"
if [[ ! "${PYTHON_VERSION}" =~ ^Python[[:space:]]+3\.([1-9][1-9]?|1[1-9][0-9]+)(\..*)?$ ]]; then
  echo "python >= 3.11 is required; found ${PYTHON_VERSION}" >&2
  exit 1
fi

if [[ ! -d "${VENV_DIR}" ]]; then
  python -m venv "${VENV_DIR}"
else
  echo "${VENV_DIR} already exists; skipping virtualenv creation"
fi

"${VENV_DIR}/bin/pip" install --no-build-isolation -e "${ROOT_DIR}"

if [[ ! -f "${ENV_FILE}" ]]; then
  cp "${ENV_EXAMPLE}" "${ENV_FILE}"
  echo "Created ${ENV_FILE} from ${ENV_EXAMPLE}"
else
  echo "${ENV_FILE} already exists; leaving it unchanged"
fi

echo "Install complete"
echo "Next: edit ${ENV_FILE} with real Slack credentials, then run scripts/start.sh"
