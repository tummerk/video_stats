# Username Enrichment Guide

## Overview

The `enrich_usernames_json.py` script enriches `usernames.json` with Instagram `user_pk` values locally, avoiding server resource usage and reducing the risk of IP bans.

**⚠️ REQUIRES AUTHENTICATION** - Instagram now requires login even for public API requests.

## Quick Start

### Basic Usage

```bash
# Run with default settings (1.5s delay)
python scripts/enrich_usernames_json.py
```

### With Custom Delay

```bash
# Recommended for large batches (2s delay)
python scripts/enrich_usernames_json.py --delay 2
```

### Force Restart

```bash
# Ignore existing output and start from beginning
python scripts/enrich_usernames_json.py --force
```

### Custom Files

```bash
# Specify input/output files
python scripts/enrich_usernames_json.py \
    --input my_usernames.json \
    --output my_usernames_with_pks.json
```

## Features

### ✨ Automatic Deduplication
- Removes duplicate usernames automatically
- Preserves first occurrence order
- Shows duplicate count in output

### 🔄 Resume Capability
- Continues from where it left off
- Skips already processed usernames
- No manual intervention needed

### 📊 Progress Tracking
- Real-time progress percentage
- ETA (estimated time arrival)
- Success/error counters
- Detailed error reporting

### ⚱️ Rate Limiting
- Configurable delay between requests
- Default: 1.5 seconds (safe for Instagram)
- Recommended: 2 seconds for large batches

## Output Format

The script creates `usernames_with_pks.json`:

```json
[
  {
    "username": "__diditee__",
    "user_pk": 123456789
  },
  {
    "username": "_karsten",
    "user_pk": 987654321
  },
  {
    "username": "nonexistent_user",
    "user_pk": null,
    "error": "User not found"
  }
]
```

## Example Output

```
Loaded 270 usernames from usernames.json
Found 32 duplicate usernames (will be removed)
Processing 238 unique usernames

Authenticating with Instagram...
✓ Authenticated successfully

[1/238] Processing: __diditee__
   Progress: 0.4% | ETA: 5m 56s | Success: 0 | Errors: 0
   → user_pk: 123456789
[2/238] Processing: _karsten
   Progress: 0.8% | ETA: 5m 54s | Success: 1 | Errors: 0
   → user_pk: 987654321
...

================================================================================
ENRICHMENT COMPLETE
================================================================================
Total usernames: 238
Successfully resolved: 231
Failed: 7
Time taken: 6m 18s
================================================================================

✓ Results saved to usernames_with_pks.json
```

## Deployment

### Step 1: Run Locally

```bash
python scripts/enrich_usernames_json.py
```

### Step 2: Verify Results

```bash
# Check file exists and has content
ls -lh usernames_with_pks.json

# Preview first few entries
head -n 20 usernames_with_pks.json
```

### Step 3: Deploy to Server

```bash
# Copy file to server
scp usernames_with_pks.json user@server:/opt/video_stats/

# SSH into server
ssh user@server

# Initialize database with enriched data
docker compose run --rm admin python scripts/init_accounts.py usernames_with_pks.json

# Verify results
docker compose exec admin psql ${DATABASE_URL} \
    -c "SELECT id, username FROM accounts LIMIT 10;"
```

## Command-Line Options

| Option | Default | Description |
|--------|---------|-------------|
| `--input` | `usernames.json` | Input JSON file with usernames |
| `--output` | `usernames_with_pks.json` | Output JSON file with results |
| `--delay` | `1.5` | Delay between requests (seconds) |
| `--force` | `False` | Ignore existing output, restart from beginning |

## Time Estimates

| Usernames | Delay | Estimated Time |
|-----------|-------|----------------|
| 50 | 1.5s | ~1.5 minutes |
| 100 | 1.5s | ~2.5 minutes |
| 238 | 1.5s | ~6 minutes |
| 238 | 2.0s | ~8 minutes |

## Error Handling

The script continues processing even when individual usernames fail:

- **Failed usernames** are saved with `user_pk: null` and `error` field
- **Final report** lists all failed usernames with error messages
- **Resume capability** allows re-running only failed usernames

## Requirements

- Python 3.8+
- `.env` file with Instagram credentials (username/password or sessionid)
- Required dependencies (from requirements.worker.txt)

### Setup Credentials

Create `.env` file in project root:

```bash
# Method 1: Username/Password (RECOMMENDED)
INSTAGRAM_USERNAME=your_username
INSTAGRAM_PASSWORD=your_password

# Method 2: Session ID (alternative)
# INSTAGRAM_SESSIONID=your_sessionid
# INSTAGRAM_CSRFTOKEN=your_csrftoken
```

## Troubleshooting

### Authentication Error

```
Error: No valid credentials. Please set INSTAGRAM_SESSIONID or INSTAGRAM_USERNAME/INSTAGRAM_PASSWORD
```

**Solution:** Check your `.env` file contains valid Instagram credentials.

### Rate Limit Error

```
Error: Rate limit exceeded
```

**Solution:** Increase delay: `--delay 3` or `--delay 5`

## Best Practices

1. **Start with default delay** (1.5s) - safe for most cases
2. **Use resume capability** - don't use `--force` unless necessary
3. **Run during off-peak hours** - reduces rate limit risk
4. **Save output file** - can be reused for database initialization
5. **Check error report** - investigate repeated failures

## Related Scripts

- `scripts/get_user_pks.py` - Alternative script for text files
- `scripts/init_accounts.py` - Initialize accounts from enriched JSON
