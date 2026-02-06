#!/usr/bin/env python3
"""Полный диагностический скрипт с захардкожеными настройками."""
import asyncio
import logging
from pathlib import Path
import sys

# Настройка логов
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =============================================================================
# ЗАХАРДКОЖЕНЫЕ НАСТРОЙКИ - ОТРЕДАКТИРУЙТЕ ЭТО!
# =============================================================================

HARDCODED = {
    # Instagram sessionid - ПОЛУЧИТЕ НОВЫЙ ИЗ БРАУЗЕРА!
    # F12 → Application → Cookies → sessionid → скопируйте Value
    "sessionid": "77937472037%3AItx4cHu9fsEeZI%3A10%3AAYiv09RrV5V_YKxPvCUqsG2QerBw2eNkp_5oC2nn4w",

    # CSRFTOKEN из браузера (опционально)
    "csrftoken": "PJ0X6SaQXIC3PtcHvdnRPkyZGJFTWfl1",

    # Прокси
    "proxy": "socks5h://Zt6cYt1A:9Pktk5xm@193.135.117.21:10000",

    # Тестовый аккаунт для проверки
    "test_username": "__diditee__",
    "test_user_pk": 304884398,
}

# =============================================================================
# КОД - НЕ МЕНЯТЬ
# =============================================================================

try:
    from instagrapi import Client
    from instagrapi.exceptions import (
        LoginRequired,
        ChallengeRequired,
        FeedbackRequired,
    )
except ImportError:
    print("ERROR: instagrapi not installed!")
    print("Install: pip install instagrapi")
    sys.exit(1)


async def test_instagram_connection():
    """Тест подключения к Instagram."""
    print("=" * 80)
    print(" ИНСТАГРАМ ДИАГНОСТИКА С ЗАХАРДКОЖЕНЫМИ НАСТРОЙКАМИ ".center(80))
    print("=" * 80)

    print(f"\n📋 Настройки:")
    print(f"  - SessionID: {HARDCODED['sessionid'][:30]}...")
    print(f"  - CSRFTOKEN: {HARDCODED['csrftoken'][:20]}...")
    print(f"  - Прокси: {HARDCODED['proxy']}")
    print(f"  - Тестовый аккаунт: @{HARDCODED['test_username']} (id={HARDCODED['test_user_pk']})")

    # Инициализация клиента
    print("\n🔧 Шаг 1: Инициализация Instagram клиента...")
    client = Client()

    # Настройка прокси
    print(f"🌐 Шаг 2: Настройка прокси: {HARDCODED['proxy']}")
    try:
        client.set_proxy(HARDCODED['proxy'])
        print("✅ Прокси установлен")
    except Exception as e:
        print(f"❌ Ошибка установки прокси: {e}")
        print("⚠️  Продолжаем без прокси...")

    # Попытка аутентификации
    print(f"\n🔐 Шаг 3: Аутентификация через SessionID...")

    try:
        # Метод 1: login_by_sessionid (только sessionid)
        print(f"   Пробуем метод: login_by_sessionid...")
        await asyncio.to_thread(client.login_by_sessionid, HARDCODED['sessionid'])
        print("✅ Аутентификация успешна!")
        authenticated = True

    except Exception as e:
        print(f"❌ Ошибка login_by_sessionid: {type(e).__name__}: {e}")

        # Попробуем через загрузку настроек
        try:
            print(f"\n   Пробуем метод: load_settings + manual_session_set...")

            # Установка sessionid вручную
            client.session_id = HARDCODED['sessionid']
            client.settings = {
                "cookies": {
                    "sessionid": HARDCODED['sessionid'],
                    "csrftoken": HARDCODED['csrftoken'],
                }
            }

            # Проверка подключения
            print("   Проверяем подключение...")
            await asyncio.to_thread(client.get_timeline_feed)
            print("✅ Аутентификация успешна!")
            authenticated = True

        except Exception as e2:
            print(f"❌ Ошибка второго метода: {type(e2).__name__}: {e2}")
            authenticated = False

    if not authenticated:
        print("\n" + "=" * 80)
        print(" ❌ АУТЕНТИФИКАЦИЯ НЕ ПОЛУЧИЛАСЬ ".center(80))
        print("=" * 80)
        print("\n💡 Возможные решения:")
        print("  1. SessionID истёк - получите новый из браузера")
        print("  2. Прокси не работает - попробуйте без прокси")
        print("  3. Instagram заблокировал IP - используйте другой прокси")
        return

    # Получение видео
    print(f"\n📹 Шаг 4: Получение видео от @{HARDCODED['test_username']}...")

    try:
        user_clips = await asyncio.to_thread(
            client.user_clips_v1,
            HARDCODED['test_user_pk'],
            amount=5
        )
        print(f"✅ Получено {len(user_clips)} видео!")

        if user_clips:
            print(f"\n📊 Пример видео:")
            for i, clip in enumerate(user_clips[:3], 1):
                print(f"  {i}. {clip.code} - {clip.media_type} - лайки: {clip.like_count}")

    except Exception as e:
        print(f"❌ Ошибка получения видео: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

    # Проверка подключения к базе (опционально)
    print(f"\n💾 Шаг 5: Проверка подключения к базе данных...")
    try:
        from src.config import settings
        from src.database.session import get_session
        from src.repositories.account_repository import AccountRepository

        print(f"   БД: {settings.database_url[:50]}...")

        async with get_session() as session:
            account_repo = AccountRepository(session)
            accounts = await account_repo.get_all()
            print(f"✅ Подключение к БД успешно!")
            print(f"   Найдено аккаунтов: {len(accounts)}")

    except Exception as e:
        print(f"❌ Ошибка подключения к БД: {type(e).__name__}: {e}")

    print("\n" + "=" * 80)
    print(" ✅ ДИАГНОСТИКА ЗАВЕРШЕНА ".center(80))
    print("=" * 80)


if __name__ == "__main__":
    try:
        asyncio.run(test_instagram_connection())
    except KeyboardInterrupt:
        print("\n⚠️  Прервано пользователем")
    except Exception as e:
        print(f"\n❌ Фатальная ошибка: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
