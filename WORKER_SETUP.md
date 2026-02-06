# Unified Worker Setup Guide

Complete guide for setting up and running `unified_worker.py` with `InstagramService`.

## Quick Start

Choose your setup method:

### Option 1: Automated Setup (Recommended)
```bash
python start_worker.py
```
This interactive script will guide you through the entire setup process.

### Option 2: Manual Setup
Follow the step-by-step instructions below.

---

## Prerequisites

- Python 3.8+
- PostgreSQL 12+
- Instagram account (for authentication)

---

## Step 1: Environment Configuration

### Create .env file
```bash
cp .env.example .env
```

### Edit .env and set required variables

#### Required: Database
```bash
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/your_database
```

#### Required: Instagram Authentication (choose one)

**Method 1: Session ID (Recommended)**
```bash
INSTAGRAM_SESSIONID=your_sessionid_here
INSTAGRAM_CSRFTOKEN=your_csrftoken_here  # Optional
```

How to get Session ID:
1. Open Instagram in browser (incognito mode recommended)
2. Login to your account
3. Press F12 → Application tab → Cookies
4. Find `sessionid` cookie and copy its value
5. Paste in `.env` file

**Method 2: Username/Password**
```bash
INSTAGRAM_USERNAME=your_username
INSTAGRAM_PASSWORD=your_password
```

#### Optional: Worker Configuration
```bash
WORKER_INTERVAL_HOURS=6       # Default: 6
WORKER_REELS_LIMIT=50         # Default: 50
AUDIO_DIR=audio               # Default: audio
```

#### Optional: Proxy
```bash
INSTAGRAM_PROXY=http://user:pass@host:port
```

---

## Step 2: Install Dependencies

### Using pip
```bash
pip install sqlalchemy asyncpg psycopg2-binary instagrapi yt-dlp apscheduler python-dotenv pydantic-settings alembic
```

### Or using requirements.txt (if available)
```bash
pip install -r requirements.txt
```

---

## Step 3: Database Setup

### Create Database
```bash
# PostgreSQL
createdb your_database_name
```

### Run Migrations
```bash
alembic upgrade head
```

Expected tables:
- `accounts`
- `videos`
- `metrics`
- `metric_schedules`

### Create Directories
```bash
mkdir -p audio
```

---

## Step 4: Add Instagram Accounts

You need to add accounts to track. There are several ways:

### Option A: Using Python Script
Create `add_account.py`:
```python
import asyncio
from src.database.session import get_session
from src.repositories.account_repository import AccountRepository

async def add_account(username, user_pk):
    async with get_session() as session:
        repo = AccountRepository(session)
        account = await repo.create_account(
            username=username,
            user_pk=user_pk
        )
        await session.commit()
        print(f"Added account: {username} (ID: {account.id})")

# Usage: python add_account.py username user_pk
asyncio.run(add_account("some_username", 12345678))
```

### Option B: Direct SQL
```bash
psql -U user -d dbname -c "INSERT INTO accounts (id, username) VALUES (12345678, 'username');"
```

**Note:** The `id` field is the Instagram user_pk (numeric ID).

---

## Step 5: Verify Setup

### Run Environment Checker
```bash
python check_environment.py
```

This will verify:
- ✅ .env file exists and has required variables
- ✅ Python dependencies installed
- ✅ Directories created
- ✅ Database connection works
- ✅ Tables exist
- ✅ Accounts in database
- ✅ Worker imports successfully

### Run Database Test (without Instagram API)
```bash
python test_database_only.py
```

This tests database functionality without calling Instagram API.

### Run Mock Test (without Instagram API)
```bash
python test_worker_mock.py
```

This tests worker logic with mocked Instagram responses.

---

## Step 6: Start the Worker

### Basic Start
```bash
python unified_worker.py
```

### With Logging
```bash
python unified_worker.py 2>&1 | tee worker.log
```

### Expected Output
```
============================================================
STARTING UNIFIED WORKER
============================================================
  - Process metrics: every 1 minute
  - Update schedules: every 1 hour
  - Fetch videos: every 6 hours
Scheduler started
Running initial tasks...
Starting fetch_new_videos task
Found X accounts in database
Processing account: username (id=12345)
...
WORKER IS RUNNING
Press Ctrl+C to stop
```

---

## Worker Tasks

The unified worker runs three tasks:

### 1. Process Metrics (every 1 minute)
- Executes pending metric collection schedules
- Fetches view/like/comment counts from Instagram
- Saves snapshots to database

### 2. Update Schedules (every 1 hour)
- Creates metric collection schedules for videos
- Adjusts schedule intervals based on video age

### 3. Fetch New Videos (every 6 hours)
- Fetches recent reels from tracked accounts
- Downloads audio using yt-dlp
- Creates metric schedules for new videos

## Schedule Intervals

Metrics collection frequency decreases over time:

| Video Age | Collection Interval |
|-----------|---------------------|
| 0-1 hours | Every 1 hour |
| 1-7 hours | Every 2 hours |
| 7-31 hours | Every 12 hours |
| 2+ days | Every 1 day |

---

## Troubleshooting

### Authentication Errors

**Error:** `LoginRequired` or `AuthenticationError`
- **Cause:** Invalid sessionid or credentials
- **Solution:** Get fresh sessionid from browser

**Error:** `ChallengeRequired`
- **Cause:** 2FA enabled or account flagged
- **Solution:**
  - Disable 2FA temporarily
  - Use different account
  - Use proxy

### Network Errors

**Error:** `NetworkError` or `FeedbackRequired`
- **Cause:** Provider blocks Instagram or rate limit
- **Solution:**
  - Use proxy: `INSTAGRAM_PROXY=http://user:pass@host:port`
  - Wait and retry later
  - Test with mock scripts (above)

### Database Errors

**Error:** `connection refused`
- **Solution:** Check PostgreSQL is running

**Error:** `relation "accounts" does not exist`
- **Solution:** Run `alembic upgrade head`

**Error:** `No accounts found`
- **Solution:** Add accounts to database (see Step 4)

### Import Errors

**Error:** `No module named 'xxx'`
- **Solution:** Install missing dependencies (see Step 2)

---

## Testing Without Instagram API

If your provider blocks Instagram or you want to test without API calls:

### 1. Test Database Only
```bash
python test_database_only.py
```

### 2. Test with Mock Data
```bash
python test_worker_mock.py
```

### 3. Verify Imports
```bash
python -c "from unified_worker import UnifiedWorker; print('OK')"
```

---

## Monitoring

### Check Worker Status
Worker logs show:
- ✅ Successful operations
- ⚠️  Warnings (e.g., no accounts)
- ❌ Errors (with full traceback)

### Check Database
```bash
# Count accounts
psql -U user -d dbname -c "SELECT COUNT(*) FROM accounts;"

# Count videos
psql -U user -d dbname -c "SELECT COUNT(*) FROM videos;"

# Count metrics
psql -U user -d dbname -c "SELECT COUNT(*) FROM metrics;"

# View recent metrics
psql -U user -d dbname -c "SELECT * FROM metrics ORDER BY recorded_at DESC LIMIT 10;"
```

---

## Advanced Configuration

### Change Worker Intervals
Edit `unified_worker.py`:

```python
# For testing: fetch videos every 1 minute instead of 6 hours
apsched.add_job(worker.fetch_new_videos, 'interval', minutes=1)
```

### Adjust Rate Limits
Edit `unified_worker.py`:

```python
class UnifiedWorker:
    DELAY_BETWEEN_ACCOUNTS = 10  # seconds between accounts
    DELAY_BETWEEN_METRICS = 0.5  # seconds between metrics
```

---

## File Structure

```
video_stats/
├── .env                          # Environment configuration
├── .env.example                  # Environment template
├── unified_worker.py             # Main worker script
├── check_environment.py          # Setup verification tool
├── start_worker.py               # Interactive setup script
├── test_database_only.py         # Database test (no Instagram API)
├── test_worker_mock.py           # Mock test (no Instagram API)
├── SETUP_WORKER.md               # Detailed setup documentation
├── WORKER_SETUP.md               # This file
├── alembic.ini                   # Database migrations config
├── alembic/
│   └── versions/                 # Migration scripts
├── audio/                        # Downloaded audio files
├── src/
│   ├── config.py                 # Configuration settings
│   ├── database/
│   │   └── session.py            # Database session
│   ├── models/                   # SQLAlchemy models
│   ├── repositories/             # Database repositories
│   └── services/
│       └── instagram_service.py  # Instagram API wrapper
└── instagram_settings.json       # Instagram session file (auto-generated)
```

---

## Support

### Getting Help

1. Run environment checker: `python check_environment.py`
2. Check logs for errors
3. Review troubleshooting section above
4. Test with mock scripts to isolate issues

### Common Issues

| Issue | Solution |
|-------|----------|
| Can't connect to database | Check DATABASE_URL and PostgreSQL status |
| Authentication fails | Get fresh sessionid from browser |
| No videos fetched | Add accounts to database |
| Provider blocks Instagram | Use proxy or test with mock scripts |

---

## Security Notes

- **Never commit `.env` file to version control**
- Keep Instagram credentials secure
- Use strong database passwords
- Consider using read-only database credentials for worker
- Rotate sessionid periodically if needed

---

## Next Steps

After successful setup:

1. ✅ Verify worker is running: `python check_environment.py`
2. ✅ Monitor logs for any errors
3. ✅ Check database for collected metrics
4. ✅ Add more accounts to track (optional)
5. ✅ Adjust worker intervals as needed (optional)

For detailed documentation, see `SETUP_WORKER.md`.
