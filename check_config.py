"""Test script to check if cookies are loaded from .env"""

from src.config import settings

print("=== Configuration Check ===\n")

print("DATABASE_URL:", settings.database_url)
print()

print("Instagram Cookies:")
print(f"  SESSIONID: {settings.instagram_sessionid[:20]}... (truncated)")
print(f"  DS_USER_ID: {settings.instagram_ds_user_id}")
print(f"  CSRFTOKEN: {settings.instagram_csrftoken}")
print(f"  MID: {settings.instagram_mid}")

# Check new cookies
try:
    print(f"  RUR: {getattr(settings, 'instagram_rur', 'NOT FOUND')}")
    print(f"  IG_DID: {getattr(settings, 'instagram_ig_did', 'NOT FOUND')}")
    print(f"  DATR: {getattr(settings, 'instagram_datr', 'NOT FOUND')}")
except Exception as e:
    print(f"  Error checking new cookies: {e}")

print()
print("All cookies loaded:", bool(
    settings.instagram_sessionid and
    settings.instagram_ds_user_id and
    settings.instagram_csrftoken and
    settings.instagram_mid
))
