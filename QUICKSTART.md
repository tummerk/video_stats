# NEW_VIDEO Worker - Quick Reference

## Setup (One-Time)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Copy environment template
cp .env.example .env

# 3. Edit .env with your values:
#    - DATABASE_URL (PostgreSQL connection)
#    - INSTAGRAM_* cookies (from browser DevTools)

# 4. Run database migrations
alembic upgrade head

# 5. Run setup wizard
python setup_worker.py
```

## Daily Usage

```bash
# Add new accounts to track
python add_account.py username1 username2

# Run worker continuously (with scheduler)
python worker_new_video.py

# Run once (no scheduler)
python -c 'import asyncio; from worker_new_video import fetch_and_process_reels; asyncio.run(fetch_and_process_reels())'
```

## Troubleshooting

```bash
# Test configuration
python test_worker.py

# Check database
# SELECT COUNT(*) FROM videos;
# SELECT * FROM accounts;

# Check audio files
ls -la audio/

# Update dependencies
pip install --upgrade yt-dlp instaloader
```

## Getting Instagram Cookies

1. Open Instagram in browser
2. Press F12 (DevTools)
3. Application > Cookies > instagram.com
4. Copy: sessionid, ds_user_id, csrftoken, mid

## Common Issues

| Issue | Solution |
|-------|----------|
| No accounts found | Run `python add_account.py username` |
| Audio download fails | Update cookies in .env |
| Transcription fails | Install FFmpeg |
| Database error | Check DATABASE_URL, run `alembic upgrade head` |

## Files

| File | Purpose |
|------|---------|
| `worker_new_video.py` | Main worker |
| `setup_worker.py` | Setup wizard |
| `test_worker.py` | Test configuration |
| `add_account.py` | Add accounts |
| `WORKER_README.md` | Full documentation |
| `IMPLEMENTATION_SUMMARY.md` | Implementation details |

## Configuration

Edit `.env`:
```
WORKER_INTERVAL_HOURS=6      # How often to run
WORKER_REELS_LIMIT=50        # Max reels per account
AUDIO_DIR=audio              # Where to save audio
```
