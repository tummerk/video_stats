import instaloader
import itertools
import getpass
import sys
import time  # Добавили модуль time

# --- НАСТРОЙКИ ---
TARGET_USERNAME = "t_01_31"
MY_USERNAME = "pavvvluv"  # Уже указан ваш логин
REELS_LIMIT = 50


# -----------------


def get_user_reels_list():
    """
    Собирает информацию о последних видео (Reels) пользователя.
    """
    L = instaloader.Instaloader()



    print(f"🔍 Начинаю поиск последних {REELS_LIMIT} видео в профиле: {TARGET_USERNAME}")

    reels_found = []
    posts_checked = 0

    try:

        post=instaloader.Post.from_shortcode(L.context,"DUA6LiYDQtu")

        if post.is_video:
            reels_found.append({
                "url": f"https://www.instagram.com/p/{post.shortcode}/",
                "views": post.video_play_count,
                "likes": post.likes,
                "caption": (post.caption or "Без описания")[:100] + "..."
            })
            print(reels_found)



    # ------------------ ИСПРАВЛЕНИЕ ЗДЕСЬ ------------------
    except instaloader.exceptions.ProfileNotExistsException:
        print(f"\n[ОШИБКА] Профиль с именем {TARGET_USERNAME} не существует.")
        sys.exit(1)
    # ---------------------------------------------------------
    except Exception as e:
        print(f"\n[ОШИБКА] Произошла ошибка во время поиска: {e}")
        sys.exit(1)

    # --- Вывод результатов ---
    if not reels_found:
        print("В профиле не найдено ни одного видео.")
        return

    print("\n" + "=" * 60)
    print(f"    СПИСОК ПОСЛЕДНИХ {len(reels_found)} ВИДЕО ПОЛЬЗОВАТЕЛЯ {TARGET_USERNAME}")
    print("=" * 60)

    for i, reel in enumerate(reels_found):
        print(f"\n#{i + 1}")
        print(f"  🔗 Ссылка: {reel['url']}")
        # Добавляем обработку None для просмотров и лайков
        views_str = f"{reel['views']:,}" if reel['views'] is not None else "N/A"
        likes_str = f"{reel['likes']:,}" if reel['likes'] is not None else "N/A"
        print(f"  👀 Просмотры: {views_str} | ❤️ Лайки: {likes_str}")
        print(f"  📝 Описание: {reel['caption']}")
        print("-" * 60)


if __name__ == "__main__":
    get_user_reels_list()
