#!/bin/sh
set -eu

# Ensure PYTHONPATH includes the /app directory
export PYTHONPATH="/app:$PYTHONPATH"

echo "[chatbot-service] Starting container..."

cd /app || { echo "Failed to cd into /app"; exit 1; }

echo "[chatbot-service] Checking database connectivity (service will continue if DB is unavailable) ..."
python -c "from app.db.session import initialize_database; initialize_database()"

echo "[chatbot-service] Syncing projects registry into PostgreSQL ..."
python scripts/sync_projects_to_db.py || echo "[chatbot-service] Project sync skipped because database is unavailable."

BOOTSTRAP_INDEX_ON_START=${BOOTSTRAP_INDEX_ON_START:-0}
INDEX_PROJECTS=${INDEX_PROJECTS:-tb}
CHUNKING_STRATEGY=${CHUNKING_STRATEGY:-semantic}

if [ "$BOOTSTRAP_INDEX_ON_START" = "1" ]; then
  echo "[chatbot-service] Bootstrapping chunks and pgvector index for projects: $INDEX_PROJECTS"
  for PROJECT_ID in $(echo "$INDEX_PROJECTS" | tr ',' ' '); do
    echo "[chatbot-service] Building chunks for project: $PROJECT_ID (strategy: $CHUNKING_STRATEGY)"
    python scripts/chunk_markdown.py --project "$PROJECT_ID" --chunking-strategy "$CHUNKING_STRATEGY"

    echo "[chatbot-service] Indexing embeddings to PostgreSQL for project: $PROJECT_ID"
    python scripts/embed_and_index.py --project "$PROJECT_ID"
  done
  echo "[chatbot-service] Index bootstrap complete."
else
  echo "[chatbot-service] BOOTSTRAP_INDEX_ON_START is disabled; skipping chunk and index bootstrap."
fi

echo "[chatbot-service] Starting Uvicorn on 0.0.0.0:8000 ..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
