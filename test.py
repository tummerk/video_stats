import instaloader
import time

L = instaloader.Instaloader(
    download_videos=False,
    download_comments=False,
    save_metadata=False
)

# Только нужные куки (без проблемных символов)
cookies = {
    "sessionid": "77937472037%3AAw4MCD7pCWtiQM%3A10%3AAYhi8IyqRQqMJP4PIf6iP5BJEVDsqkM4EIrSRX2FyQ",
    "ds_user_id": "77937472037",
    "csrftoken": "zRXlCWjdkAHNbF-bToqNdC",
    "mid": "aXpJDwALAAEmKkf6O0Q-Tf8FfkgG",
}

for name, value in cookies.items():
    L.context._session.cookies.set(
        name,
        value,
        domain=".instagram.com",
        path="/",
        secure=True
    )

# Тест
try:
    profile = instaloader.Profile.from_username(L.context, "grownahhboy")
    reels=profile.get_reels()
    for reel in reels:
        print(f"https://www.instagram.com/reel/{reel.shortcode}/")
except Exception as e:
    print(f"Ошибка: {e}")