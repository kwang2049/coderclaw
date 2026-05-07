#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANIFEST_FILE="${ROOT_DIR}/manifest.json"

if [[ ! -f "${MANIFEST_FILE}" ]]; then
  echo "Missing manifest file: ${MANIFEST_FILE}" >&2
  exit 1
fi

if [[ -z "${SLACK_CONFIG_TOKEN:-}" ]]; then
  echo "SLACK_CONFIG_TOKEN is required" >&2
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required but was not found in PATH" >&2
  exit 1
fi

MANIFEST_JSON="$(jq -c . "${MANIFEST_FILE}")"

curl -sS -X POST "https://slack.com/api/apps.manifest.validate" \
  -H "Authorization: Bearer ${SLACK_CONFIG_TOKEN}" \
  -H "Content-Type: application/json; charset=utf-8" \
  -d "{\"manifest\": ${MANIFEST_JSON}}"
echo
