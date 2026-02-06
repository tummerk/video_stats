# Инструкция: Получение user_pk с авторизацией

## Что делает скрипт?

Берёт файл `usernames.json` со списком Instagram usernames и находит для каждого их числовой ID (user_pk), сохраняя результат в `usernames_with_pks.json`.

**⚠️ ТРЕБУЕТ АВТОРИЗАЦИЮ** - Нужны логин и пароль от Instagram.

## Использование

### Базовая команда
```bash
python scripts/enrich_usernames_json.py
```

### С увеличенной задержкой (безопаснее)
```bash
python scripts/enrich_usernames_json.py --delay 2
```

### Начать заново
```bash
python scripts/enrich_usernames_json.py --force
```

## Установка credentials

Перед запуском создай файл `.env` в корне проекта:

```bash
# Скопируй пример
cp .env.example .env
```

Отредактируй `.env` и добавь свои credentials:

```bash
# Метод 1: Логин/Пароль (РЕКОМЕНДУЕТСЯ)
INSTAGRAM_USERNAME=твой_юзернейм
INSTAGRAM_PASSWORD=твой_пароль

# Метод 2: Session ID (альтернатива)
# INSTAGRAM_SESSIONID=твой_sessionid
# INSTAGRAM_CSRFTOKEN=твой_csrftoken
```

## Пример работы

```
Loaded 270 usernames from usernames.json
Found 32 duplicate usernames (will be removed)
Processing 238 unique usernames

Authenticating with Instagram...
✓ Authenticated successfully

[1/238] Processing: __diditee__
   Progress: 0.4% | ETA: 5m 56s | Success: 0 | Errors: 0
   → user_pk: 123456789
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

## Что на входе?

**usernames.json:**
```json
[
  "__diditee__",
  "_karsten",
  "abramovavl"
]
```

## Что на выходе?

**usernames_with_pks.json:**
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

## Возможности

1. **Автоматически удаляет дубликаты** - 270 usernames → 238 уникальных
2. **Показывает прогресс** - Процент, ETA, количество успехов/ошибок
3. **Можно продолжить** - Если прервётся, продолжит с того же места
4. **Обрабатывает ошибки** - При ошибке с одним username продолжает с другими

## Опции командной строки

| Опция | По умолчанию | Описание |
|-------|--------------|----------|
| `--input` | `usernames.json` | Входной JSON файл |
| `--output` | `usernames_with_pks.json` | Выходной JSON файл |
| `--delay` | `1.5` | Задержка между запросами (секунды) |
| `--force` | `false` | Начать заново, игнорируя существующий файл |

## Время выполнения

| Usernames | Задержка | Примерное время |
|-----------|----------|-----------------|
| 50 | 1.5s | ~1.5 минут |
| 100 | 1.5s | ~2.5 минут |
| 238 | 1.5s | ~6 минут |
| 238 | 2.0s | ~8 минут |

## Дальнейшие шаги

После получения `usernames_with_pks.json`:

```bash
# 1. Скопировать на сервер
scp usernames_with_pks.json user@server:/opt/video_stats/

# 2. Инициализировать базу данных
docker compose run --rm admin python scripts/init_accounts.py usernames_with_pks.json

# 3. Проверить результат
docker compose exec admin psql ${DATABASE_URL} \
    -c "SELECT id, username FROM accounts LIMIT 10;"
```

## Требования

- Python 3.8+
- Файл `.env` с Instagram credentials (логин/пароль или sessionid)
- Установленные зависимости (из `requirements.worker.txt`):
  ```bash
  pip install -r requirements.worker.txt
  ```

## Преимущества

1. **Локальное выполнение** - Не нагружает сервер
2. **Без авторизации** - Не нужны логин/пароль
3. **Переиспользование** - Результат можно сохранить и использовать снова
4. **Надёжность** - Обрабатывает ошибки без остановки

## Рекомендации

1. Используй задержку **1.5-2 секунды** между запросами
2. Запускай в непиковые часы
3. Проверяй файл `usernames_with_pks.json` после выполнения
4. При ошибках увеличивай задержку: `--delay 3`
