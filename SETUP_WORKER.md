# План: Проверка и настройка окружения для unified_worker.py

## Цель

Обеспечить корректный запуск `unified_worker.py` после переписывания с использованием `InstagramService`.

---

## Обязательные переменные окружения (.env)

### База данных (обязательно)
```bash
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/dbname
```

### Worker конфигурация
```bash
WORKER_INTERVAL_HOURS=6       # Как часто проверять новые видео
WORKER_REELS_LIMIT=50         # Макс. количество видео для проверки
AUDIO_DIR=audio               # Директория для audio файлов
```

### Instagram аутентификация (instagrapi)
**Достаточно одного из способов:**

**Способ 1: Session ID (рекомендуется)**
```bash
INSTAGRAM_SESSIONID=your_sessionid_here
INSTAGRAM_CSRFTOKEN=your_csrftoken_here  # Опционально
```

**Способ 2: Username/Password**
```bash
INSTAGRAM_USERNAME=your_username
INSTAGRAM_PASSWORD=your_password
```

### Опционально
```bash
INSTAGRAM_PROXY=http://user:pass@host:port  # Прокси (если нужно)
INSTAGRAM_SETTINGS_FILE=instagram_settings.json  # Файл для сохранения сессии
```

### yt-dlp настройки
```bash
# Не обязательно в .env - используется дефолтное значение yt_dlp_max_workers=2
```

---

## Как получить Session ID

1. Откройте Instagram в браузере (в режиме инкогнито или после выхода)
2. Войдите в аккаунт
3. Откройте DevTools (F12) → Application/Хранилище → Cookies
4. Найдите cookie `sessionid`
5. Скопируйте значение в `INSTAGRAM_SESSIONID`

---

## Предварительные проверки

### 1. Проверка базы данных
```bash
# Убедитесь, что PostgreSQL запущен
psql -U user -d dbname -c "SELECT 1;"

# Проверьте наличие таблиц
psql -U user -d dbname -c "\dt"
```

Ожидаемые таблицы:
- `accounts`
- `videos`
- `metrics`
- `metric_schedules`

### 2. Проверка наличия аккаунтов в БД
```bash
psql -U user -d dbname -c "SELECT id, username FROM accounts;"
```

Должен быть хотя бы один аккаунт для отслеживания.

### 3. Создание директории для audio
```bash
mkdir -p audio
```

---

## Запуск worker

### Базовый запуск
```bash
python unified_worker.py
```

### Запуск с логированием в файл
```bash
python unified_worker.py 2>&1 | tee worker.log
```

---

## Проверка корректности запуска

### Ожидаемый вывод при старте

```
============================================================
STARTING UNIFIED WORKER
============================================================
  - Process metrics: every 1 minute
  - Update schedules: every 1 hour
  - Fetch videos: every 6 hours
Scheduler started
Running initial tasks...
Starting fetch_new_videos task
Found X accounts in database
Processing account: username (id=12345)
...
WORKER IS RUNNING
Press Ctrl+C to stop
```

### Что проверить

1. **Аутентификация Instagram**
   - ✅ Успех: Лог содержит `Authenticated via sessionid` или `Authenticated as username`
   - ❌ Ошибка: `AuthenticationError` → проверить `INSTAGRAM_SESSIONID`
   - ❌ Ошибка: `NetworkError` / `ChallengeRequired` → провайдер блокирует, использовать прокси или тестировать без API

2. **Соединение с БД**
   - ✅ Успех: `Found X accounts in database`
   - ❌ Ошибка: `connection refused` → проверить PostgreSQL
   - ❌ Ошибка: `relation "accounts" does not exist` → запустить миграции

3. **Создание расписаний**
   - ✅ Успех: Лог содержит `Created schedule for XYZ (age: Nd) at ...`

### Если Instagram API заблокирован провайдером

**Вариант А:** Продолжить тестирование - worker корректно обработает ошибку и продолжит работу с другими задачами (scheduler, metrics processing).

**Вариант Б:** Добавить прокси в `.env`:
```bash
INSTAGRAM_PROXY=http://user:pass@host:port
```

**Вариант В:** Тестировать только функционал БД без Instagram (см. "Тестирование без Instagram API" выше).

---

## Возможные ошибки и решения

| Ошибка | Причина | Решение |
|--------|---------|---------|
| `LoginRequired` | Недействительный sessionid | Получить новый `sessionid` из браузера |
| `ChallengeRequired` | 2FA или блокировка | Использовать другой аккаунт/прокси |
| `FeedbackRequired` | Rate limit / блокировка провайдера | Подождать или использовать прокси |
| `UserNotFound` | Неверный user_pk | Проверить `account.id` в БД |
| `No accounts found` | Пустая база | Добавить аккаунты через админку |
| `relation does not exist` | Нет таблиц | Запустить `alembic upgrade head` |
| `NetworkError` | Провайдер блокирует Instagram | Использовать прокси или тестировать без API |
| `No module named 'instagrapi'` | Нет зависимостей | Установить пакеты (список ниже) |

---

## Тестирование без Instagram API (если провайдер блокирует)

### Вариант 1: Тестовая проверка импортов
```bash
python -c "from unified_worker import UnifiedWorker; print('OK')"
```
Должно вывести `OK` без ошибок импорта.

### Вариант 2: Проверка соединения с БД (без Instagram)
```python
import asyncio
from src.database.session import get_session
from src.repositories.account_repository import AccountRepository

async def test_db():
    async with get_session() as session:
        repo = AccountRepository(session)
        accounts = await repo.get_all()
        print(f"Found {len(accounts)} accounts in DB")

asyncio.run(test_db())
```

### Вариант 3: Mock тест для InstagramService
Создать файл `test_worker_mock.py`:
```python
import asyncio
from unittest.mock import AsyncMock, MagicMock
from unified_worker import UnifiedWorker

async def test_without_instagram():
    worker = UnifiedWorker()

    # Заменяем методы InstagramService на моки
    worker.instagram_service.get_user_recent_videos = AsyncMock(return_value=None)
    worker.instagram_service.get_video_metrics = AsyncMock(
        return_value=MagicMock(
            view_count=1000,
            like_count=50,
            comment_count=10,
            followers_count=5000
        )
    )

    # Тестируем только логику worker
    await worker.update_metric_schedules()
    print("Worker logic test: OK")

asyncio.run(test_without_instagram())
```

### Вариант 4: Использование прокси
Если провайдер блокирует Instagram, добавить в `.env`:
```bash
INSTAGRAM_PROXY=http://proxy_user:proxy_pass@proxy_host:proxy_port
```

---

## Зависимости Python

Установить необходимые пакеты:
```bash
pip install sqlalchemy asyncpg psycopg2-binary instagrapi yt-dlp whisper-openai apscheduler python-dotenv pydantic-settings
```

Или из requirements (если существует):
```bash
pip install -r requirements.txt
```

---

## Тестовый запуск без ожидания

Изменить временно интервалы для быстрого теста:
```python
# В unified_worker.py временно:
apsched.add_job(worker.fetch_new_videos, 'interval', minutes=1)  # вместо hours
```

---

## Критические файлы

| Файл | Зачем |
|------|-------|
| `.env` | Переменные окружения |
| `unified_worker.py` | Главный worker |
| `src/services/instagram_service.py` | Instagram сервис (не изменять!) |
| `src/config.py` | Конфигурация приложения |
| `src/database/session.py` | Сессия БД |

---

## План действий

1. ✅ Создать `.env` файл с правильными значениями
2. ✅ Убедиться, что PostgreSQL запущен и создана база данных
3. ✅ Установить зависимости Python
4. ✅ Добавить хотя бы один аккаунт для отслеживания (в БД)
5. ✅ Создать директорию `audio/`
6. ✅ Запустить `python unified_worker.py`
7. ✅ Проверить логи на наличие ошибок
8. ✅ Убедиться, что создаются записи в `metric_schedules`
