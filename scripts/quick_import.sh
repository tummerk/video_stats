#!/bin/bash
# Quick script to import accounts before starting docker-compose

set -e

echo "=================================="
echo "IMPORT ACCOUNTS TO DATABASE"
echo "=================================="

# Get PostgreSQL container name
POSTGRES_CONTAINER=$(docker ps --filter "name=postgres" --format "{{.Names}}" | head -1)

if [ -z "$POSTGRES_CONTAINER" ]; then
    echo "❌ ERROR: PostgreSQL container not found!"
    echo "   Please start PostgreSQL first"
    exit 1
fi

echo "✅ Found PostgreSQL: $POSTGRES_CONTAINER"
echo ""

# Import accounts
docker run --rm \
  --network container:$POSTGRES_CONTAINER \
  -v $(pwd)/scripts:/app/scripts \
  -v $(pwd)/src:/app/src \
  -e DATABASE_URL=postgresql+asyncpg://user:passd@$POSTGRES_CONTAINER:5432/reels \
  python:3.11-slim \
  sh -c "
    echo 'Installing dependencies...'
    pip install -q asyncpg sqlalchemy
    echo 'Importing accounts...'
    python /app/scripts/import_accounts.py
  "

echo ""
echo "=================================="
echo "✅ DONE! Now run:"
echo "   docker-compose up -d"
echo "=================================="
