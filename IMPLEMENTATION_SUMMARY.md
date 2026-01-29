# NEW_VIDEO Worker Implementation Summary

## Overview

The NEW_VIDEO worker has been successfully implemented. It fetches the latest Instagram Reels for all accounts in the database every 6 hours, enriches them with audio transcription using OpenAI Whisper, and saves them to the database.

## Files Created

### Core Implementation
1. **`worker_new_video.py`** - Main worker implementation
   - Scheduled execution every 6 hours
   - Fetches reels for all accounts
   - Downloads and transcribes audio
   - Saves to database
   - Error handling and logging

2. **`src/config.py`** (updated) - Added worker configuration settings
   - Worker interval, reels limit, audio directory
   - Instagram cookie settings

### Configuration Files
3. **`.env.example`** (updated) - Environment variable template
   - Added worker and Instagram cookie variables

4. **`requirements.txt`** (new) - Python dependencies
   - All required packages listed

### Helper Scripts
5. **`test_worker.py`** - Test worker configuration
   - Verify environment variables
   - Test Instagram client
   - Test database connection

6. **`setup_worker.py`** - Interactive setup wizard
   - Check configuration
   - Create directories
   - Add test accounts

7. **`add_account.py`** - Quick account addition
   - Add Instagram accounts from CLI

### Documentation
8. **`WORKER_README.md`** - Complete documentation
   - Installation instructions
   - Usage examples
   - Troubleshooting guide

9. **`audio/`** - Directory for audio files
   - Created automatically

## Key Features Implemented

### ✅ Core Functionality
- Fetches latest 50 reels per account (configurable)
- Skips existing videos (by shortcode)
- Downloads audio to `audio/{shortcode}.mp3`
- Transcribes audio using Whisper
- Saves enriched data to database
- Auto-creates accounts if missing

### ✅ Scheduling
- APScheduler for 6-hour intervals
- Runs immediately on startup
- Continuous execution until stopped

### ✅ Error Handling
- Continues on individual video failures
- Logs all errors
- Rolls back database transactions on error
- Handles Instagram API limits

### ✅ Smart Processing
- Breaks loop on first existing video per account
- Processes accounts sequentially (avoids rate limits)
- 2-second delay between accounts

## Architecture

```
worker_new_video.py
│
├── create_instaloader_client()
│   └── Configures Instaloader with cookies from .env
│
├── enrich_reel_data(url, shortcode)
│   ├── Downloads audio via yt-dlp
│   ├── Extracts video/audio URLs
│   └── Transcribes with Whisper
│
├── process_account_reels()
│   ├── Fetches reels from Instagram
│   ├── Checks if video exists in DB
│   ├── Enriches new videos
│   └── Saves to database
│
├── fetch_and_process_reels()
│   ├── Gets all accounts from DB
│   └── Processes each account
│
└── main()
    ├── Sets up APScheduler
    ├── Runs initial job
    └── Keeps scheduler running
```

## Database Schema

Uses existing `videos` table:
- `video_id` - Instagram video ID (unique)
- `shortcode` - Instagram shortcode (unique)
- `video_url` - Direct video URL
- `published_at` - Publication timestamp
- `caption` - Video caption
- `duration_seconds` - Video duration
- `audio_url` - Direct audio URL
- `audio_file_path` - Local MP3 path
- `transcription` - Transcribed text
- `account_id` - Foreign key to accounts

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
# Copy .env.example to .env
cp .env.example .env

# Edit .env with your values:
# - DATABASE_URL
# - INSTAGRAM_SESSIONID
# - INSTAGRAM_DS_USER_ID
# - INSTAGRAM_CSRFTOKEN
# - INSTAGRAM_MID
```

### 3. Run Setup Wizard
```bash
python setup_worker.py
```

### 4. Add Accounts
```bash
python add_account.py username1 username2
```

### 5. Test Configuration
```bash
python test_worker.py
```

### 6. Run Worker
```bash
# Run continuously with scheduler
python worker_new_video.py

# Or run once without scheduler
python -c 'import asyncio; from worker_new_video import fetch_and_process_reels; asyncio.run(fetch_and_process_reels())'
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | ✅ | - | PostgreSQL connection string |
| `INSTAGRAM_SESSIONID` | ✅ | - | Instagram session cookie |
| `INSTAGRAM_DS_USER_ID` | ✅ | - | Instagram user ID cookie |
| `INSTAGRAM_CSRFTOKEN` | ✅ | - | Instagram CSRF token |
| `INSTAGRAM_MID` | ✅ | - | Instagram MID cookie |
| `WORKER_INTERVAL_HOURS` | ❌ | 6 | Hours between runs |
| `WORKER_REELS_LIMIT` | ❌ | 50 | Max reels per account |
| `AUDIO_DIR` | ❌ | audio | Audio files directory |

## Verification Steps

All verification steps from the plan are implemented:

1. ✅ **Test Instagram client** - `python test_worker.py`
2. ✅ **Test single account processing** - Run `fetch_and_process_reels()` once
3. ✅ **Verify audio files** - Check `audio/` directory
4. ✅ **Verify database** - Query `videos` table
5. ✅ **Run worker continuously** - `python worker_new_video.py`
6. ✅ **Check scheduler** - Monitor logs

## Testing

### Test Instagram Client
```bash
python -c "from worker_new_video import create_instaloader_client; L = create_instaloader_client(); print('OK')"
```

### Test Single Account
```bash
python -c "import asyncio; from worker_new_video import fetch_and_process_reels; asyncio.run(fetch_and_process_reels())"
```

### Verify Audio Files
```bash
ls -la audio/
```

### Verify Database
```python
import asyncio
from src.database import get_session
from src.repositories.video_repository import VideoRepository

async def check():
    async with get_session() as s:
        repo = VideoRepository(s)
        videos = await repo.get_all()
        print(f'Total videos: {len(videos)}')

asyncio.run(check())
```

## Logging

Worker outputs detailed logs:
```
2024-01-29 10:00:00 - worker_new_video - INFO - Starting fetch_and_process_reels job
2024-01-29 10:00:01 - worker_new_video - INFO - Found 3 accounts in database
2024-01-29 10:00:02 - worker_new_video - INFO - Processing account: username1
2024-01-29 10:00:05 - worker_new_video - INFO - Processing new reel: ABC123
```

## Troubleshooting

### Issue: "No accounts found"
**Solution**: Add accounts using `python add_account.py username`

### Issue: "Failed to download audio"
**Solution**:
1. Refresh Instagram cookies
2. Update yt-dlp: `pip install --upgrade yt-dlp`
3. Check network connection

### Issue: "Transcription fails"
**Solution**:
1. Install FFmpeg
2. Check disk space
3. Verify audio file was downloaded

## Next Steps

The worker is fully implemented and ready to use. To get started:

1. Run the setup wizard: `python setup_worker.py`
2. Test configuration: `python test_worker.py`
3. Add accounts: `python add_account.py username`
4. Run worker: `python worker_new_video.py`

For full documentation, see `WORKER_README.md`.

## Implementation Complete

All requirements from the plan have been implemented:
- ✅ Scheduled worker (6-hour intervals)
- ✅ Fetches 50 latest reels per account
- ✅ Skips existing videos
- ✅ Audio enrichment (yt-dlp + Whisper)
- ✅ Saves to audio/ directory
- ✅ Database persistence
- ✅ Auto-creates accounts
- ✅ Error handling
- ✅ Logging
- ✅ Configuration via environment
- ✅ Helper scripts
- ✅ Documentation
