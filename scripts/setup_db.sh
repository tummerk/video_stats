#!/bin/bash
# Complete database setup script for server

set -e

echo "=================================="
echo "DATABASE SETUP"
echo "=================================="

# Step 1: Start PostgreSQL
echo ""
echo "📦 Step 1: Starting PostgreSQL..."
POSTGRES_CONTAINER=$(docker ps -a --filter "name=postgres" --format "{{.Names}}" | head -1)

if [ -z "$POSTGRES_CONTAINER" ]; then
    echo "Creating new PostgreSQL container..."
    docker run -d \
      --name postgres \
      --restart unless-stopped \
      -e POSTGRES_USER=user \
      -e POSTGRES_PASSWORD=passd \
      -e POSTGRES_DB=reels \
      -p 5432:5432 \
      -v postgres_data:/var/lib/postgresql/data \
      postgres:15

    POSTGRES_CONTAINER="postgres"
    echo "Waiting for PostgreSQL to start..."
    sleep 5
else
    echo "Found existing container: $POSTGRES_CONTAINER"
    docker start $POSTGRES_CONTAINER 2>/dev/null || true
fi

echo "✅ PostgreSQL: $POSTGRES_CONTAINER"

# Step 2: Test connection
echo ""
echo "🔗 Step 2: Testing connection..."
docker exec -it $POSTGRES_CONTAINER psql -U user -d reels -c "SELECT 1;" > /dev/null 2>&1 || {
    echo "❌ Cannot connect to database"
    exit 1
}
echo "✅ Database connection OK"

# Step 3: Apply migrations
echo ""
echo "🔄 Step 3: Applying migrations..."
docker run --rm \
  --network container:$POSTGRES_CONTAINER \
  -v $(pwd)/src:/app/src \
  -v $(pwd)/alembic:/app/alembic \
  -v $(pwd)/alembic.ini:/app/alembic.ini \
  -e DATABASE_URL=postgresql+asyncpg://user:passd@$POSTGRES_CONTAINER:5432/reels \
  python:3.11-slim \
  bash -c "
    pip install -q alembic asyncpg sqlalchemy &&
    alembic upgrade head
  "

echo "✅ Migrations applied"

# Step 4: Check tables
echo ""
echo "📊 Step 4: Checking tables..."
docker exec -it $POSTGRES_CONTAINER psql -U user -d reels -c "\dt"

echo ""
echo "=================================="
echo "✅ DATABASE SETUP COMPLETE!"
echo "=================================="
echo ""
echo "Next steps:"
echo "  1. Import accounts: bash scripts/quick_import.sh"
echo "  2. Start system:    docker-compose up -d"
echo ""
