# Быстрый старт: Enrich usernames

## 1. Настройка credentials

Создай файл `.env` в корне проекта:

```bash
INSTAGRAM_USERNAME=твой_юзернейм
INSTAGRAM_PASSWORD=твой_пароль
```

Или используй sessionid (альтернатива):

```bash
INSTAGRAM_SESSIONID=твой_sessionid
INSTAGRAM_CSRFTOKEN=твой_csrftoken
```

## 2. Запуск скрипта

```bash
# Базовая команда
python scripts/enrich_usernames_json.py

# С задержкой 2 секунды (рекомендуется)
python scripts/enrich_usernames_json.py --delay 2
```

## 3. Результат

Создастся файл `usernames_with_pks.json`:

```json
[
  {
    "username": "__diditee__",
    "user_pk": 123456789
  },
  ...
]
```

## 4. Деплой на сервер

```bash
# Скопировать файл
scp usernames_with_pks.json user@server:/opt/video_stats/

# Инициализировать БД
docker compose run --rm admin python scripts/init_accounts.py usernames_with_pks.json
```

## Опции

| Флаг | Описание |
|------|----------|
| `--delay 2` | Задержка 2 сек между запросами (безопаснее) |
| `--force` | Начать заново, игнорируя существующий файл |
| `--input файл.json` | Указать входной файл |
| `--output файл.json` | Указать выходной файл |

## Ошибки

**login_required** → Проверь credentials в `.env`
**Rate limit exceeded** → Увеличь задержку `--delay 3`
**Challenge required** → Используй другой аккаунт или подожди

## Время работы

- **238 usernames** × 2 сек = **~8 минут**
