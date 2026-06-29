#!/bin/sh
set -eu

export PYTHONPATH="/app:${PYTHONPATH:-}"

APP_NAME=${APP_NAME:-helpcentre}
APP_HOST=${APP_HOST:-0.0.0.0}
APP_PORT=${APP_PORT:-8000}
WAIT_FOR_DB=${WAIT_FOR_DB:-1}
DB_WAIT_TIMEOUT_SECONDS=${DB_WAIT_TIMEOUT_SECONDS:-90}
RUN_PROJECT_SYNC=${RUN_PROJECT_SYNC:-1}
BOOTSTRAP_INDEX_ON_START=${BOOTSTRAP_INDEX_ON_START:-0}
INDEX_PROJECTS=${INDEX_PROJECTS:-tb,cervical_cancer}
CHUNKING_STRATEGY=${CHUNKING_STRATEGY:-semantic}
FORCE_RECHUNK=${FORCE_RECHUNK:-0}

log() {
  echo "[$APP_NAME] $*"
}

wait_for_database() {
  if [ "$WAIT_FOR_DB" != "1" ]; then
    log "WAIT_FOR_DB disabled; continuing without waiting for PostgreSQL."
    return 0
  fi

  log "Waiting for PostgreSQL readiness, timeout=${DB_WAIT_TIMEOUT_SECONDS}s ..."
  START_TS=$(date +%s)
  while :; do
    if python -c "from app.db.session import initialize_database; raise SystemExit(0 if initialize_database() else 1)" >/dev/null 2>&1; then
      log "PostgreSQL is ready."
      return 0
    fi

    NOW_TS=$(date +%s)
    ELAPSED=$((NOW_TS - START_TS))
    if [ "$ELAPSED" -ge "$DB_WAIT_TIMEOUT_SECONDS" ]; then
      log "PostgreSQL was not ready after ${DB_WAIT_TIMEOUT_SECONDS}s."
      return 1
    fi
    sleep 3
  done
}

sync_projects() {
  if [ "$RUN_PROJECT_SYNC" != "1" ]; then
    log "RUN_PROJECT_SYNC disabled; skipping project registry sync."
    return 0
  fi

  log "Syncing project registry into PostgreSQL ..."
  python scripts/sync_projects_to_db.py
}

index_projects() {
  log "Building chunks and pgvector indexes for projects: $INDEX_PROJECTS"
  for PROJECT_ID in $(echo "$INDEX_PROJECTS" | tr ',' ' '); do
    if [ "$FORCE_RECHUNK" = "1" ]; then
      log "Chunking project=$PROJECT_ID strategy=$CHUNKING_STRATEGY"
      python scripts/chunk_markdown.py --project "$PROJECT_ID" --chunking-strategy "$CHUNKING_STRATEGY"
    else
      log "Using existing chunk files for project=$PROJECT_ID when present. Set FORCE_RECHUNK=1 to rebuild them."
      python scripts/chunk_markdown.py --project "$PROJECT_ID" --chunking-strategy "$CHUNKING_STRATEGY" --skip-existing
    fi

    log "Indexing project=$PROJECT_ID"
    python scripts/embed_and_index.py --project "$PROJECT_ID" --resume
  done
  log "Indexing complete."
}

start_api() {
  log "Starting API on ${APP_HOST}:${APP_PORT} ..."
  exec uvicorn app.main:app --host "$APP_HOST" --port "$APP_PORT"
}

COMMAND=${1:-api}
cd /app

case "$COMMAND" in
  api)
    if ! wait_for_database; then
      log "Database unavailable; API will start in degraded mode."
    else
      sync_projects || log "Project registry sync failed; API will still start."
    fi

    if [ "$BOOTSTRAP_INDEX_ON_START" = "1" ]; then
      index_projects || log "Index bootstrap failed; API will still start."
    else
      log "BOOTSTRAP_INDEX_ON_START disabled; skipping startup indexing."
    fi

    start_api
    ;;
  index)
    wait_for_database
    sync_projects
    index_projects
    ;;
  sync-projects)
    wait_for_database
    sync_projects
    ;;
  *)
    log "Running custom command: $*"
    exec "$@"
    ;;
esac
