#!/bin/sh
set -e

# Ensure DATABASE_URL uses the asyncpg driver (render auto-sets DATABASE_URL with postgres://)
if [ -n "$DATABASE_URL" ]; then
  export DATABASE_URL=$(echo "$DATABASE_URL" | sed 's|^postgres://|postgresql+asyncpg://|;s|^postgresql://|postgresql+asyncpg://|')
elif [ -n "$DATABASE_URL_SYNC" ]; then
  export DATABASE_URL=$(echo "$DATABASE_URL_SYNC" | sed 's|^postgres://|postgresql+asyncpg://|;s|^postgresql://|postgresql+asyncpg://|')
fi

# Ensure DATABASE_URL_SYNC uses standard sync driver for Alembic
if [ -n "$DATABASE_URL_SYNC" ]; then
  export DATABASE_URL_SYNC=$(echo "$DATABASE_URL_SYNC" | sed 's|^postgres://|postgresql://|;s|^postgresql+asyncpg://|postgresql://|')
elif [ -n "$DATABASE_URL" ]; then
  export DATABASE_URL_SYNC=$(echo "$DATABASE_URL" | sed 's|^postgresql+asyncpg://|postgresql://|')
fi

echo "Running Alembic migrations..."
alembic upgrade head

echo "Starting uvicorn on port ${PORT:-8000}..."
exec uvicorn src.main:app --host 0.0.0.0 --port "${PORT:-8000}"
