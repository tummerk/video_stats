# Docker Deployment Guide for Instagram Reels Tracker

## Overview

This guide covers deploying the Instagram Reels Tracker to a remote Ubuntu/Debian server using Docker Compose.

The application consists of:
- **Admin Panel** (FastAPI + Jinja2) - web interface on port 8000
- **Worker** (unified_worker.py) - background service for collecting metrics
- **PostgreSQL** - already installed on the server

## Important: Account ID Structure

**Critical:** The `Account` model uses Instagram `user_pk` as the primary key (NOT auto-increment)!
- `Account.id` = Instagram user_pk (integer ID from Instagram)
- This means when creating accounts, you must provide their user_pk
- Without correct user_pk, the worker cannot download videos

## Prerequisites

### On the server, ensure you have:
- Docker Engine (20.10+)
- Docker Compose (2.0+)
- PostgreSQL (already installed)
- Nginx (optional, for reverse proxy)

### Check Docker installation:
```bash
docker --version
docker compose version
```

---

## Quick Deployment Steps

### 1. Prepare the Server

```bash
# SSH to server
ssh user@your-server-ip

# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker (if not installed)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose (if not installed)
sudo apt install docker-compose-plugin -y

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Verify installation
docker --version
docker compose version
```

### 2. Clone and Configure Project

```bash
# Clone repository
git clone <your-repo-url> /opt/video_stats
cd /opt/video_stats

# Copy and edit .env
cp .env.example .env
nano .env  # Edit with your values

# Create directories
mkdir -p audio logs cookies
```

### 3. Setup PostgreSQL

```bash
# Connect to PostgreSQL
sudo -u postgres psql

# Create database and user
CREATE DATABASE instagram_tracker;
CREATE USER tracker_user WITH PASSWORD 'secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE instagram_tracker TO tracker_user;
\q
```

### 4. Prepare Accounts Data (CRITICAL!)

#### Step A: Get user_pk values (on your local machine)

Create a file with usernames:
```bash
cat > usernames.txt << 'EOF'
instagram
some_account
another_account
EOF
```

Get user_pk values:
```bash
python scripts/get_user_pks.py usernames.txt -o user_pks.json
```

Check the output file `user_pks.json`:
```json
[
  {
    "username": "instagram",
    "user_pk": 25025320
  },
  {
    "username": "some_account",
    "user_pk": 123456789
  }
]
```

#### Step B: Copy to server and initialize

```bash
# On server - copy the user_pks.json file
scp user_pks.json user@server:/opt/video_stats/

# On server - run database migrations
cd /opt/video_stats
docker compose run --rm admin alembic upgrade head

# Initialize accounts with proper user_pk
docker compose run --rm admin python scripts/init_accounts.py user_pks.json

# Verify accounts have correct IDs (user_pk values, not 1,2,3...)
docker compose exec admin psql ${DATABASE_URL} -c "SELECT id, username FROM accounts;"
```

**Expected output:**
```
      id     |  username
------------+------------
  25025320   | instagram
  123456789  | some_account
```

If you see small IDs (1, 2, 3...), the accounts were created incorrectly and the worker won't work!

### 5. Build and Start Containers

```bash
# Build images
docker compose build

# Start services
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f
```

### 6. Verify Deployment

```bash
# Check containers are running
docker compose ps

# Test admin panel
curl http://localhost:8000/dashboard

# Check worker logs
docker compose logs worker | head -50

# Check database
docker compose exec admin alembic current
```

---

## Management Commands

### Docker Compose Commands

```bash
# View status
docker compose ps

# View logs
docker compose logs -f              # All services
docker compose logs -f admin        # Admin only
docker compose logs -f worker       # Worker only

# Restart services
docker compose restart admin
docker compose restart worker

# Stop services
docker compose stop

# Start services
docker compose start

# Rebuild after changes
docker compose up -d --build

# Stop and remove containers
docker compose down
```

### Database Management

```bash
# Run migrations
docker compose exec admin alembic upgrade head

# Rollback migrations
docker compose exec admin alembic downgrade -1

# Create new migration
docker compose exec admin alembic revision --autogenerate -m "description"

# Connect to database
docker compose exec admin psql ${DATABASE_URL}
```

---

## Troubleshooting

### Container cannot connect to PostgreSQL

**Solution:** Use special host for Linux:
```yaml
# Add to docker-compose.yml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

Then update DATABASE_URL:
```bash
DATABASE_URL=postgresql+asyncpg://user:pass@host.docker.internal:5432/dbname
```

### Worker not starting

**Check:**
```bash
# Worker logs
docker compose logs worker

# Environment variables
docker compose exec worker env | grep INSTAGRAM

# Enter container
docker compose exec worker bash
```

### Admin panel not responding

**Check:**
```bash
# Container status
docker compose ps admin

# Logs
docker compose logs admin

# Restart
docker compose restart admin
```

### No tables in database

**Solution:** Run migrations
```bash
docker compose exec admin alembic upgrade head
```

---

## Security

### Setup Firewall

```bash
# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS (if using Nginx)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable
sudo ufw status
```

### SSL with Let's Encrypt (optional)

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx -y

# Get certificate
sudo certbot --nginx -d your-domain.com
```

### Protect .env file

```bash
chmod 600 .env
chown $USER:$USER .env
```

---

## Auto-start on Boot

Docker Compose is configured with `restart: unless-stopped` for automatic startup.

Verify:
```bash
# Check Docker service
sudo systemctl status docker

# Check containers
docker compose ps
```

---

## Whisper and Transcription

The worker uses OpenAI's Whisper for audio transcription. By default, it installs the full PyTorch library which can be large (~2GB).

### CPU-Only Installation (Recommended for servers)

To reduce the Docker image size, you can use CPU-only PyTorch:

**Option 1: Modify requirements.worker.txt**
```bash
# Uncomment the CPU-only torch line in requirements.worker.txt
# torch==2.1.0+cpu --extra-index-url https://download.pytorch.org/whl/cpu
```

**Option 2: Set environment variable**
```bash
# In .env or docker-compose.yml
export PIP_INDEX_URL=https://pypi.org/simple/
export PIP_EXTRA_INDEX_URL=https://download.pytorch.org/whl/cpu
```

**Option 3: Manual installation in Dockerfile**
```dockerfile
# In Dockerfile.worker, before pip install:
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu
```

The worker uses the "base" Whisper model by default, which is the smallest (~140MB). CPU-only inference is slower but sufficient for most use cases.

### Changing Whisper Model

Edit `src/services/instagram_service.py`:
```python
# Line ~259: Change model size
self._whisper_model = whisper.load_model("base")  # Options: tiny, base, small, medium, large
```

---

## Files Created for Deployment

1. `admin/main.py` - FastAPI entry point
2. `.dockerignore` - Docker exclusions
3. `Dockerfile.admin` - Admin container image
4. `Dockerfile.worker` - Worker container image
5. `requirements.admin.txt` - Admin dependencies
6. `requirements.worker.txt` - Worker dependencies
7. `docker-compose.yml` - Container orchestration
8. `scripts/get_user_pks.py` - Resolve usernames to user_pk
9. `scripts/init_accounts.py` - Initialize accounts in database
10. `accounts_seed.json.example` - Example accounts JSON
11. `admin/routes/accounts.py` - Updated with JSON import
12. `admin/templates/accounts/json_import.html` - JSON import UI

---

## Critical Verification Steps

After deployment, verify:

1. ✅ Containers running: `docker compose ps`
2. ✅ Admin accessible: `curl http://localhost:8000/dashboard`
3. ✅ **Accounts have user_pk IDs**: Check database output shows large IDs
4. ✅ Worker running: `docker compose logs worker`
5. ✅ Migrations applied: `docker compose exec admin alembic current`

**Most common issue:** Accounts created without proper user_pk. Always verify with:
```bash
docker compose exec admin psql ${DATABASE_URL} -c "SELECT id, username FROM accounts;"
```

If IDs are small (1, 2, 3...), delete and reinitialize:
```bash
docker compose exec admin psql ${DATABASE_URL} -c "DELETE FROM accounts;"
docker compose run --rm admin python scripts/init_accounts.py user_pks.json
```
