"""
Enrich usernames.json using Session ID (more reliable than login/password).
Session ID doesn't require password and works better.

Usage:
    python scripts/enrich_with_session.py
"""

import asyncio
import json
from pathlib import Path
import sys
import time
from argparse import ArgumentParser
from datetime import timedelta

from instagrapi import Client

# =============================================================================
# КОНФИГУРАЦИЯ - Вставь свой sessionid
# =============================================================================

INSTAGRAM_SESSIONID = "77937472037%3AItx4cHu9fsEeZI%3A10%3AAYhXOkdpVkc0ei0wp2lXYb2rCMm-IBdKV8BrjpTPag"
INSTAGRAM_CSRFTOKEN = "PJ0X6SaQXIC3PtcHvdnRPkyZGJFTWfl1"

# =============================================================================
# ИНСТРУКЦИЯ: Как получить Session ID
# =============================================================================

"""
1. Открой Instagram в браузере (https://instagram.com)
2. Зайди в свой аккаунт
3. Нажми F12 (Developer Tools)
4. Перейди в вкладку "Application" / "Приложение"
5. В левом меню → Cookies → https://www.instagram.com
6. Найди cookie с именем "sessionid"
7. Скопируй его значение и вставь ниже
8. (Опционально) Также скопируй "csrftoken"

Пример:
INSTAGRAM_SESSIONID = "1234567890%3Aabcdefghijklmnopqrstuvwxyz..."
INSTAGRAM_CSRFTOKEN = "abcdefghijklmnopqrstuvwxyz123456"
"""

# =============================================================================
#СКРИПТ
# =============================================================================


class UsernameEnricher:
    """Класс для обогащения usernames.json с user_pk."""

    def __init__(self, input_file: str, output_file: str, delay: float = 1.5):
        self.input_file = Path(input_file)
        self.output_file = Path(output_file)
        self.delay = delay
        self.results = []
        self.processed_usernames = set()

    def load_input(self) -> list:
        """Загружает usernames из входного файла."""
        with open(self.input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if isinstance(data, list) and len(data) > 0:
            if isinstance(data[0], str):
                return data
            elif isinstance(data[0], dict):
                return [item.get('username') for item in data]

        return []

    def deduplicate(self, usernames: list) -> tuple[list, int]:
        """Удаляет дубликаты."""
        seen = set()
        unique = []
        duplicates = 0

        for username in usernames:
            if username not in seen:
                seen.add(username)
                unique.append(username)
            else:
                duplicates += 1

        return unique, duplicates

    def load_existing_results(self) -> dict:
        """Загружает существующие результаты."""
        if not self.output_file.exists():
            return {}

        with open(self.output_file, 'r', encoding='utf-8') as f:
            results = json.load(f)

        return {r['username']: r.get('user_pk') for r in results}

    async def enrich(self, force: bool = False):
        """Основной метод обогащения."""
        # Загрузить usernames
        usernames = self.load_input()
        print(f"Загружено {len(usernames)} usernames из {self.input_file}")

        # Дедупликация
        usernames, dup_count = self.deduplicate(usernames)
        if dup_count > 0:
            print(f"Найдено {dup_count} дубликатов (будут удалены)")
        print(f"Обработка {len(usernames)} уникальных usernames\n")

        # Загрузить существующие результаты
        if not force:
            existing = self.load_existing_results()
            if existing:
                print(f"Найден выходной файл: {self.output_file}")
                print(f"Уже обработано: {len(existing)} usernames")
                self.processed_usernames = set(existing.keys())
                self.results = [
                    {"username": uname, "user_pk": pk}
                    for uname, pk in existing.items()
                ]
                print(f"Продолжение с последнего обработанного username...\n")
        else:
            print("Режим force: начинаем с начала\n")

        # Инициализировать клиент
        print("Инициализация Instagram клиента...")
        client = Client()

        # Устанавливаем cookies напрямую
        print("Установка cookies...")
        client.settings = {
            "cookies": {
                "sessionid": INSTAGRAM_SESSIONID,
                "csrftoken": INSTAGRAM_CSRFTOKEN,
                "ds_user_id": "77937472037",
                "ig_did": "A5C17C38-A3B8-48ED-9A58-28A5543889BC",
                "mid": "aXpJDwALAAEmKkf6O0Q-Tf8FfkgG",
                "rur": '"LLA\\05477937472037\\0541801833751:01fe128d644e82f6a59201fecd0a855f9922b6fbee36ec2a4c310808e3baca298e94aaa4"',
            },
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        }
        print("✓ Cookies установлены\n")

            # Обработать usernames
            start_time = time.time()
            success_count = len(self.processed_usernames)
            error_count = 0

            for idx, username in enumerate(usernames, 1):
                # Пропустить если уже обработан
                if username in self.processed_usernames:
                    continue

                try:
                    # Показать прогресс
                    self.print_progress(
                        idx, len(usernames), username,
                        success_count, error_count, start_time
                    )

                    # Получить user_pk
                    user_pk = await asyncio.to_thread(
                        client.user_id_from_username,
                        username
                    )

                    self.results.append({
                        "username": username,
                        "user_pk": user_pk
                    })
                    success_count += 1

                    print(f"   → user_pk: {user_pk}")

                    # Rate limiting
                    await asyncio.sleep(self.delay)

                except Exception as e:
                    error_count += 1
                    self.results.append({
                        "username": username,
                        "user_pk": None,
                        "error": str(e)
                    })
                    print(f"   ✗ Ошибка: {e}")

            # Финальный отчёт
            elapsed = time.time() - start_time
            self.print_final_report(len(usernames), success_count, error_count, elapsed)

        finally:
            # Сохранить сессию
            try:
                settings_file = Path("cookies/instagram_settings.json")
                settings_file.parent.mkdir(parents=True, exist_ok=True)
                await asyncio.to_thread(client.dump_settings, str(settings_file))
                print(f"\n✓ Сессия сохранена в {settings_file}")
            except Exception as e:
                print(f"\n⚠ Не удалось сохранить сессию: {e}")

    def save_results(self):
        """Сохраняет результаты."""
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        print(f"✓ Результаты сохранены в {self.output_file}")

    def print_progress(self, current: int, total: int, username: str,
                      success_count: int, error_count: int, start_time: float):
        """Показывает прогресс."""
        elapsed = time.time() - start_time
        if current > 0:
            eta = (elapsed / current) * (total - current)
        else:
            eta = 0

        print(f"[{current}/{total}] Обработка: {username}")
        print(f"   Прогресс: {current/total*100:.1f}% | "
              f"ETA: {self.format_time(eta)} | "
              f"Успешно: {success_count} | Ошибок: {error_count}")

    def print_final_report(self, total: int, success: int, errors: int, elapsed: float):
        """Финальный отчёт."""
        print("\n" + "=" * 80)
        print("ОБОГАЩЕНИЕ ЗАВЕРШЕНО")
        print("=" * 80)
        print(f"Всего usernames: {total}")
        print(f"Успешно разрешено: {success}")
        print(f"Неудач: {errors}")
        print(f"Время выполнения: {self.format_time(elapsed)}")
        print("=" * 80)

        if errors > 0:
            print("\nНеудачные usernames:")
            for r in self.results:
                if not r.get('user_pk'):
                    error = r.get('error', 'Неизвестная ошибка')
                    print(f"  - @{r['username']}: {error}")

    @staticmethod
    def format_time(seconds: float) -> str:
        """Форматирует секунды в человекочитаемый формат."""
        td = timedelta(seconds=int(seconds))
        total_seconds = int(td.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours}ч {minutes}м {seconds}с"


def main():
    parser = ArgumentParser(
        description="Обогатить usernames.json с user_pk значениями"
    )
    parser.add_argument(
        "--input",
        default="usernames.json",
        help="Входной JSON файл (default: usernames.json)"
    )
    parser.add_argument(
        "--output",
        default="usernames_with_pks.json",
        help="Выходной JSON файл (default: usernames_with_pks.json)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.5,
        help="Задержка между запросами в секундах (default: 1.5)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Начать заново, игнорировать существующий файл"
    )

    args = parser.parse_args()

    # Проверить входной файл
    if not Path(args.input).exists():
        print(f"Ошибка: Файл не найден: {args.input}")
        sys.exit(1)

    # Проверить credentials
    if not INSTAGRAM_SESSIONID or INSTAGRAM_SESSIONID == "":
        print("\n" + "=" * 80)
        print("ОШИБКА: Не указан Session ID!")
        print("=" * 80)
        print("\nОткрой файл scripts/enrich_with_session.py и:")
        print("  1. Открой Instagram в браузере")
        print("  2. Нажми F12 → Application → Cookies → instagram.com")
        print("  3. Найди 'sessionid' и скопируй его значение")
        print("  4. Вставь в INSTAGRAM_SESSIONID = '...'\n")
        sys.exit(1)

    # Создать энричер
    enricher = UsernameEnricher(args.input, args.output, args.delay)

    # Запустить обогащение
    asyncio.run(enricher.enrich(force=args.force))

    # Сохранить результаты
    enricher.save_results()


if __name__ == "__main__":
    main()
