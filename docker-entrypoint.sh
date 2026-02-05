#!/bin/bash
set -e

echo "🔄 Waiting for PostgreSQL..."
until PGPASSWORD=user pg_isready -h db -p 5432 -U user > /dev/null 2>&1; do
  echo "  PostgreSQL not ready yet..."
  sleep 2
done

echo "✅ Database is ready!"

echo "⏳ Waiting 30 seconds for database to fully initialize..."
sleep 30

echo "🔄 Running database migrations..."
alembic upgrade head

echo "✅ Migrations complete!"

echo "🚀 Starting worker..."
exec "$@"
