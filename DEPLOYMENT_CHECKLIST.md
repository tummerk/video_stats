# Deployment Checklist

Use this checklist to verify all files are in place before deployment.

## Files Created

### Docker Configuration
- ✅ `Dockerfile.admin` - Admin panel container image
- ✅ `Dockerfile.worker` - Worker container image
- ✅ `docker-compose.yml` - Container orchestration
- ✅ `.dockerignore` - Docker build exclusions
- ✅ `requirements.admin.txt` - Admin dependencies
- ✅ `requirements.worker.txt` - Worker dependencies (includes Whisper)

### Application Files
- ✅ `admin/main.py` - FastAPI application entry point

### Scripts
- ✅ `scripts/get_user_pks.py` - Resolve usernames to user_pk
- ✅ `scripts/init_accounts.py` - Initialize database accounts

### Templates
- ✅ `admin/templates/accounts/json_import.html` - JSON import UI

### Configuration
- ✅ `.env.production.example` - Production environment template
- ✅ `accounts_seed.json.example` - Example accounts JSON

### Documentation
- ✅ `DEPLOYMENT.md` - Full deployment guide
- ✅ `ACCOUNT_INIT_GUIDE.md` - Account initialization guide

### Modified Files
- ✅ `src/services/instagram_service.py` - Added `resolve_username_to_user_pk()` method
- ✅ `admin/routes/accounts.py` - Added JSON import endpoints

---

## Pre-Deployment Checklist

### 1. Prerequisites
- [ ] Docker 20.10+ installed on server
- [ ] Docker Compose 2.0+ installed on server
- [ ] PostgreSQL installed and accessible
- [ ] Server has at least 4GB RAM (recommended)
- [ ] Server has at least 10GB free disk space

### 2. Configuration
- [ ] `.env` file created from `.env.example`
- [ ] `DATABASE_URL` configured correctly
- [ ] Instagram credentials set (SESSIONID or USERNAME/PASSWORD)
- [ ] Optional: INSTAGRAM_PROXY configured if needed

### 3. Account Initialization (CRITICAL)
- [ ] `usernames.txt` created with Instagram usernames
- [ ] `python scripts/get_user_pks.py usernames.txt -o user_pks.json` executed
- [ ] `user_pks.json` verified (all accounts have user_pk values)
- [ ] Database migrations run: `docker compose run --rm admin alembic upgrade head`
- [ ] Accounts initialized: `docker compose run --rm admin python scripts/init_accounts.py user_pks.json`
- [ ] Database verified: `SELECT id, username FROM accounts;` shows user_pk values (not 1,2,3...)

### 4. Build and Deploy
- [ ] `docker compose build` completed successfully
- [ ] `docker compose up -d` started containers
- [ ] `docker compose ps` shows both containers as "Up"

### 5. Verification
- [ ] Admin panel accessible: `curl http://localhost:8000/dashboard`
- [ ] Worker logs show no errors: `docker compose logs worker`
- [ ] Database migrations applied: `docker compose exec admin alembic current`
- [ ] Can access admin panel in browser

### 6. Optional Security
- [ ] Firewall configured (UFW)
- [ ] SSL certificate installed (Let's Encrypt)
- [ ] Nginx reverse proxy configured
- [ ] `.env` file permissions set to 600

---

## Quick Commands Reference

### Build and Start
```bash
docker compose build
docker compose up -d
docker compose ps
```

### Check Logs
```bash
docker compose logs -f              # All services
docker compose logs -f admin        # Admin only
docker compose logs -f worker       # Worker only
```

### Database Operations
```bash
# Migrations
docker compose run --rm admin alembic upgrade head

# Check current version
docker compose exec admin alembic current

# Connect to database
docker compose exec admin psql ${DATABASE_URL}
```

### Restart Services
```bash
docker compose restart admin
docker compose restart worker
docker compose restart              # Both
```

### Stop Services
```bash
docker compose stop                 # Stop containers
docker compose down                 # Stop and remove containers
```

---

## Troubleshooting Quick Reference

| Problem | Solution |
|---------|----------|
| Containers can't connect to PostgreSQL | Use `host.docker.internal` or server IP in DATABASE_URL |
| Worker fails to start | Check `docker compose logs worker` and verify Instagram credentials |
| Admin panel not accessible | Check `docker compose ps admin` and restart if needed |
| Accounts have wrong IDs (1,2,3...) | Delete and reinitialize: `DELETE FROM accounts;` then run init script |
| No tables in database | Run migrations: `docker compose exec admin alembic upgrade head` |
| Image too large | Use CPU-only PyTorch (see DEPLOYMENT.md) |

---

## Support

For detailed troubleshooting, see:
- `DEPLOYMENT.md` - Full deployment guide
- `ACCOUNT_INIT_GUIDE.md` - Account initialization details
- Docker logs: `docker compose logs -f`
