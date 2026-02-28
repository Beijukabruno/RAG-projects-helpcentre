#!/bin/sh
set -eu

# Ensure PYTHONPATH includes the /app directory
export PYTHONPATH="/app:$PYTHONPATH"

echo "[chatbot-service] Starting container..."

cd /app || { echo "Failed to cd into /app"; exit 1; }


# Only build chunks and vector_db if not already present
if [ ! -f ./data/chunks.json ] || [ ! -d ./vector_db ] || [ -z "$(ls -A ./vector_db 2>/dev/null)" ]; then
  echo "[chatbot-service] (Re)building vector_db from knowledge_base (this may take a few minutes)..."
  if [ -f ./scripts/chunk_markdown.py ] && [ -f ./scripts/embed_and_index.py ]; then
    python scripts/chunk_markdown.py
    python scripts/embed_and_index.py
    echo "[chatbot-service]  Indexing complete — vector_db/ created."
  else
    echo "[chatbot-service]  Indexing scripts not found — cannot build vector_db. Exiting." >&2
    exit 1
  fi
else
  echo "[chatbot-service] Precomputed chunks and vector_db found, skipping rebuild."
fi

echo "[chatbot-service] Running DB migrations (creating tables if needed) ..."
python -c "from db_models import Base; from sqlalchemy import create_engine; import os; \
engine = create_engine(os.getenv('DATABASE_URL', 'postgresql://helpcentre_user:helpcentre_pass@postgres_helpcentre:5432/helpcentre_db')); \
Base.metadata.create_all(engine)"

echo "[chatbot-service] Starting Uvicorn on 0.0.0.0:8000 ..."
exec uvicorn consolidated_chatbot:app --host 0.0.0.0 --port 8000
