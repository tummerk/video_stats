# Account Initialization Quickstart

This guide explains how to properly initialize Instagram accounts with correct user_pk values.

## Why is this important?

The `Account` model uses Instagram's `user_pk` (primary key) as the database ID. If you create accounts without the correct user_pk, the worker **cannot download videos**.

## Process Overview

1. **Get user_pk values** - Resolve Instagram usernames to their numeric IDs
2. **Initialize database** - Create accounts with correct IDs
3. **Verify** - Check that accounts have proper IDs (not 1, 2, 3...)

---

## Step-by-Step Guide

### Step 1: Create Usernames List

Create a text file with one Instagram username per line:

```bash
cat > usernames.txt << 'EOF'
instagram
some_account
another_account
EOF
```

### Step 2: Get user_pk Values

Run the script to resolve usernames to user_pk:

```bash
# Local (on your machine)
python scripts/get_user_pks.py usernames.txt -o user_pks.json

# Or via Docker
docker compose run --rm admin python scripts/get_user_pks.py usernames.txt -o user_pks.json
```

### Step 3: Check Results

Open `user_pks.json` and verify:

```json
[
  {
    "username": "instagram",
    "user_pk": 25025320
  },
  {
    "username": "some_account",
    "user_pk": 123456789
  },
  {
    "username": "another_account",
    "user_pk": 987654321
  }
]
```

All accounts should have `user_pk` values (large integers).

### Step 4: Initialize Database

```bash
# Via Docker
docker compose run --rm admin python scripts/init_accounts.py user_pks.json
```

Expected output:
```
Loaded 3 accounts from user_pks.json
Authenticating with Instagram...
✓ Authenticated successfully
[1/3] Resolving user_pk for @instagram...
  → Resolved to user_pk: 25025320
  ✓ Created account: @instagram (ID: 25025320)
[2/3] Skipping some_account (already exists)
[3/3] Resolving user_pk for @another_account...
  → Resolved to user_pk: 987654321
  ✓ Created account: @another_account (ID: 987654321)

============================================================
INITIALIZATION COMPLETE
============================================================
Created:  2
Skipped:  1
Errors:   0
```

### Step 5: Verify in Database

```bash
docker compose exec admin psql ${DATABASE_URL} -c "SELECT id, username FROM accounts;"
```

**Correct output (user_pk as ID):**
```
      id     |  username
------------+------------
  25025320   | instagram
  123456789  | some_account
  987654321  | another_account
```

**Wrong output (auto-increment ID):**
```
 id |  username
----+------------
  1  | instagram
  2  | some_account
  3  | another_account
```

If you see wrong output, the worker will not work! Delete and reinitialize:
```bash
docker compose exec admin psql ${DATABASE_URL} -c "DELETE FROM accounts;"
docker compose run --rm admin python scripts/init_accounts.py user_pks.json
```

---

## Alternative: Web UI Import

You can also import accounts via the admin panel:

1. Start admin: `docker compose up -d admin`
2. Open: `http://your-server:8000/accounts/json-import`
3. Paste JSON with accounts
4. Click "Import Accounts"

The web UI will automatically resolve user_pk if not provided.

---

## JSON Format Examples

### With user_pk (faster, recommended):
```json
[
  {"username": "instagram", "user_pk": 25025320},
  {"username": "some_account", "user_pk": 123456789}
]
```

### Without user_pk (slower, auto-resolved):
```json
[
  {"username": "instagram"},
  {"username": "some_account"}
]
```

The initialization script will resolve usernames to user_pk automatically.

---

## Troubleshooting

### Script fails with authentication error

**Solution:** Check your Instagram credentials in `.env`:
```bash
INSTAGRAM_SESSIONID=your_sessionid
INSTAGRAM_CSRFTOKEN=your_csrftoken
```

### Some usernames fail to resolve

**Possible reasons:**
- Username doesn't exist
- Account is private
- Rate limiting (wait and retry)

Check `user_pks.json` for error details:
```json
{
  "username": "nonexistent_user",
  "user_pk": null,
  "error": "User not found"
}
```

### Accounts already exist

The script will skip existing accounts:
```
[2/3] Skipping some_account (already exists)
```

This is normal behavior.

---

## Summary

**Critical Rule:** Always initialize accounts with proper user_pk values!

1. Create `usernames.txt` with your accounts
2. Run `python scripts/get_user_pks.py usernames.txt -o user_pks.json`
3. Verify `user_pks.json` has all user_pk values
4. Run `docker compose run --rm admin python scripts/init_accounts.py user_pks.json`
5. Verify with `SELECT id, username FROM accounts;`

If IDs are small integers (1, 2, 3...), something went wrong and you need to reinitialize.
