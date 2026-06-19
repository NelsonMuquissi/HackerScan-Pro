#!/bin/sh
# ─── docker-entrypoint.sh ─────────────────────────────────────────────────────
# Waits for Postgres to be ready, installs any missing deps, runs migrations,
# then executes CMD.
set -e

echo "📦 Ensuring required Python packages..."
pip install --quiet --no-cache-dir markdown weasyprint 2>/dev/null || true

echo "⏳ Waiting for PostgreSQL..."
until nc -z "${POSTGRES_HOST:-db}" "${POSTGRES_PORT:-5432}"; do
  sleep 1
done
echo "✅ PostgreSQL is up."

echo "🔄 Running migrations..."
python manage.py migrate --noinput

echo "🚀 Starting server..."
exec "$@"
