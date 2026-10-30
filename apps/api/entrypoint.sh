#!/bin/sh
set -e

# Rewrite postgres:// → postgresql+asyncpg:// if DATABASE_URL wasn't set directly
if [ -z "$DATABASE_URL" ] && [ -n "$DATABASE_URL_SYNC" ]; then
  export DATABASE_URL=$(echo "$DATABASE_URL_SYNC" | sed 's|^postgres://|postgresql+asyncpg://|;s|^postgresql://|postgresql+asyncpg://|')
fi

# Normalize postgres:// → postgresql:// for Alembic / sync SQLAlchemy
if [ -n "$DATABASE_URL_SYNC" ]; then
  export DATABASE_URL_SYNC=$(echo "$DATABASE_URL_SYNC" | sed 's|^postgres://|postgresql://|')
fi

echo "Running Alembic migrations..."
alembic upgrade head

echo "Starting uvicorn on port ${PORT:-8000}..."
exec uvicorn src.main:app --host 0.0.0.0 --port "${PORT:-8000}"
