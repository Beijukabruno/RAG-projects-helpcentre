#!/bin/sh
set -eu

APP_PORT=${APP_PORT:-8000}
HEALTHCHECK_PATH=${HEALTHCHECK_PATH:-/health}

curl --fail --silent --show-error "http://localhost:${APP_PORT}${HEALTHCHECK_PATH}" >/dev/null
