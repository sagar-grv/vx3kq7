#!/bin/sh
set -e
cd /app/backend
if [ ! -s "$DB_PATH" ]; then
  echo "No database found - ingesting January 2026 Elexon data (needs network)..."
  PYTHONPATH=. python -m app.ingest
fi
PYTHONPATH=. exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
