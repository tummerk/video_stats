# NEW_VIDEO Worker

## Overview

The `worker_new_video.py` is a scheduled worker that fetches the latest Instagram Reels for all accounts in the database every 6 hours, enriches them with audio transcription, and saves them to the database.

## Features

- **Scheduled Execution**: Runs every 6 hours (configurable via `WORKER_INTERVAL_HOURS`)
- **Automatic Account Discovery**: Auto-creates accounts that don't exist in the database
- **Smart Processing**: Skips videos that already exist in the database
- **Audio Transcription**: Downloads audio and transcribes using OpenAI Whisper
- **Error Handling**: Continues processing even if individual videos fail
- **Persistent Storage**: Saves audio files to `audio/` directory

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables in `.env`:
```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/reels

# Worker Configuration
WORKER_INTERVAL_HOURS=6
WORKER_REELS_LIMIT=50
AUDIO_DIR=audio

# Instagram Cookies (get from browser dev tools)
INSTAGRAM_SESSIONID=your_sessionid_here
INSTAGRAM_DS_USER_ID=your_ds_user_id_here
INSTAGRAM_CSRFTOKEN=your_csrftoken_here
INSTAGRAM_MID=your_mid_here
```

3. Run database migrations:
```bash
alembic upgrade head
```

## Getting Instagram Cookies

1. Open Instagram in your browser
2. Open Developer Tools (F12)
3. Go to Application > Cookies > https://www.instagram.com
4. Copy the values for:
   - `sessionid`
   - `ds_user_id`
   - `csrftoken`
   - `mid`

## Usage

### Test Configuration

Before running the worker, test your configuration:

```bash
python test_worker.py
```

This will verify:
- Environment variables are set
- Instagram client can be created
- Database connection works

### Run Worker Once

To run the worker once without scheduling:

```python
import asyncio
from worker_new_video import fetch_and_process_reels

asyncio.run(fetch_and_process_reels())
```

### Run Worker Continuously

To run the worker with scheduler:

```bash
python worker_new_video.py
```

The worker will:
1. Run immediately on startup
2. Then run every 6 hours (or configured interval)
3. Continue running until stopped with Ctrl+C

## How It Works

### Processing Flow

1. **Fetch Accounts**: Gets all accounts from the database
2. **Process Each Account**:
   - Fetches latest 50 reels (configurable)
   - For each reel:
     - Checks if it exists in database (by shortcode)
     - If exists: skips to next account (assumes older videos are already processed)
     - If new:
       - Downloads audio to `audio/{shortcode}.mp3`
       - Transcribes audio using Whisper
       - Saves enriched data to database
3. **Repeat**: Waits for next scheduled run

### Database Schema

The worker saves to the `videos` table:
- `video_id`: Instagram video ID (unique)
- `shortcode`: Instagram shortcode (unique)
- `video_url`: Direct video URL
- `published_at`: Publication timestamp
- `caption`: Video caption
- `duration_seconds`: Video duration
- `audio_url`: Direct audio URL
- `audio_file_path`: Local path to downloaded MP3
- `transcription`: Transcribed text from audio
- `account_id`: Foreign key to accounts table

### Error Handling

- **Account not found/private**: Logs error, continues to next account
- **Audio download fails**: Logs error, saves video without transcription
- **Transcription fails**: Logs error, saves video without transcription
- **Database errors**: Logs error, rolls back transaction

## Monitoring

### Logs

The worker outputs detailed logs:
```
2024-01-29 10:00:00 - worker_new_video - INFO - Starting fetch_and_process_reels job
2024-01-29 10:00:01 - worker_new_video - INFO - Found 3 accounts in database
2024-01-29 10:00:02 - worker_new_video - INFO - Processing account: username1
2024-01-29 10:00:05 - worker_new_video - INFO - Processing new reel: ABC123
2024-01-29 10:00:10 - worker_new_video - INFO - Downloading audio for ABC123...
2024-01-29 10:00:15 - worker_new_video - INFO - Transcribing audio for ABC123...
2024-01-29 10:00:25 - worker_new_video - INFO - Saved reel ABC123 to database
```

### Database Queries

Check processed videos:
```sql
-- Count videos per account
SELECT a.username, COUNT(v.id) as video_count
FROM accounts a
LEFT JOIN videos v ON a.id = v.account_id
GROUP BY a.username;

-- Latest videos
SELECT v.shortcode, a.username, v.published_at, v.transcription
FROM videos v
JOIN accounts a ON v.account_id = a.id
ORDER BY v.published_at DESC
LIMIT 10;
```

## Troubleshooting

### Issue: "No accounts found in database"

**Solution**: Add accounts to the database first:
```python
import asyncio
from src.database import get_session
from src.repositories.account_repository import AccountRepository

async def add_account():
    async with get_session() as session:
        repo = AccountRepository(session)
        await repo.create(
            username="instagram_username",
            profile_url="https://www.instagram.com/username/",
            followers_count=0
        )

asyncio.run(add_account())
```

### Issue: "Failed to download audio"

**Possible causes**:
- Instagram cookies expired
- Network connectivity issues
- yt-dlp needs update

**Solutions**:
1. Refresh Instagram cookies
2. Update yt-dlp: `pip install --upgrade yt-dlp`
3. Check network connection

### Issue: "Transcription fails"

**Possible causes**:
- Insufficient disk space
- Missing FFmpeg

**Solutions**:
1. Check disk space: `df -h`
2. Install FFmpeg:
   - macOS: `brew install ffmpeg`
   - Ubuntu: `sudo apt install ffmpeg`
   - Windows: Download from https://ffmpeg.org/

## Configuration Options

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `WORKER_INTERVAL_HOURS` | 6 | Hours between runs |
| `WORKER_REELS_LIMIT` | 50 | Max reels to fetch per account |
| `AUDIO_DIR` | audio | Directory for audio files |

## Architecture

```
worker_new_video.py
├── create_instaloader_client()    # Setup Instagram API client
├── enrich_reel_data()             # Download & transcribe audio
├── process_account_reels()        # Process reels for one account
├── fetch_and_process_reels()      # Main processing logic
└── main()                         # Scheduler entry point
```

## Dependencies

- **instaloader**: Instagram data scraping
- **yt-dlp**: Audio downloading
- **openai-whisper**: Audio transcription
- **apscheduler**: Task scheduling
- **sqlalchemy**: Database ORM
- **asyncpg**: Async PostgreSQL driver

## Future Enhancements

- [ ] Add retry logic for failed downloads
- [ ] Parallel processing of accounts
- [ ] Webhook notifications for new videos
- [ ] Metrics dashboard
- [ ] Configurable Whisper model size
- [ ] Skip transcription for short videos
