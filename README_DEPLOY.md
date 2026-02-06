# Деплой Instagram Reels Tracker

## Что было создано

### Docker конфигурация
- ✅ `Dockerfile.admin` - образ контейнера для админ-панели
- ✅ `Dockerfile.worker` - образ контейнера для воркера (включая Whisper для транскрипции)
- ✅ `docker-compose.yml` - оркестрация контейнеров
- ✅ `.dockerignore` - исключения для Docker сборки
- ✅ `requirements.admin.txt` - зависимости админки
- ✅ `requirements.worker.txt` - зависимости воркера (с Whisper!)

### Файлы приложения
- ✅ `admin/main.py` - точка входа FastAPI приложения

### Скрипты для инициализации
- ✅ `scripts/get_user_pks.py` - получение user_pk по usernames
- ✅ `scripts/init_accounts.py` - инициализация аккаунтов в БД с правильными user_pk

### Шаблоны админки
- ✅ `admin/templates/accounts/json_import.html` - форма для JSON импорта аккаунтов

### Конфигурация
- ✅ `.env.production.example` - пример production конфигурации
- ✅ `accounts_seed.json.example` - пример JSON файла с аккаунтами

### Документация
- ✅ `DEPLOYMENT.md` - полное руководство по деплою (на английском)
- ✅ `ACCOUNT_INIT_GUIDE.md` - руководство по инициализации аккаунтов (на английском)
- ✅ `DEPLOYMENT_CHECKLIST.md` - чеклист для проверки

### Модифицированные файлы
- ✅ `src/services/instagram_service.py` - добавлен метод `resolve_username_to_user_pk()`
- ✅ `admin/routes/accounts.py` - добавлены endpoints для JSON импорта

---

## Важное примечание о Whisper

В `requirements.worker.txt` добавлен **openai-whisper** для транскрипции аудио.

### CPU-only версия (рекомендуется)

По умолчанию whisper установит полную версию PyTorch (~2GB). Для уменьшения размера образа:

**Вариант 1:** Раскомментировать строку в `requirements.worker.txt`:
```
torch==2.1.0+cpu --extra-index-url https://download.pytorch.org/whl/cpu
```

**Вариант 2:** Установить torch CPU версии отдельно перед установкой зависимостей.

Размеры моделей Whisper:
- `tiny` - ~39MB (самая быстрая, менее точная)
- `base` - ~140MB (используется по умолчанию)
- `small` - ~460MB
- `medium` - ~1.5GB
- `large` - ~2.9GB (самая точная, медленная)

Для смены модели отредактируйте `src/services/instagram_service.py` строка ~259:
```python
self._whisper_model = whisper.load_model("base")  # или "tiny", "small", "medium", "large"
```

---

## Критически важный момент: user_pk

Модель `Account` использует Instagram `user_pk` как primary key (НЕ auto-increment)!

**Почему это важно:**
- Без правильного user_pk воркер **не сможет скачивать видео**
- Если создать аккаунты через старую форму, они получат ID 1, 2, 3... (неправильно)
- Нужно использовать новые скрипты для инициализации

**Правильный процесс:**

1. Создать файл `usernames.txt`:
```
instagram
some_account
another_account
```

2. Получить user_pk:
```bash
python scripts/get_user_pks.py usernames.txt -o user_pks.json
```

3. Проверить `user_pks.json`:
```json
[
  {"username": "instagram", "user_pk": 25025320},
  {"username": "some_account", "user_pk": 123456789}
]
```

4. Инициализировать БД:
```bash
docker compose run --rm admin python scripts/init_accounts.py user_pks.json
```

5. Проверить в БД:
```bash
docker compose exec admin psql ${DATABASE_URL} -c "SELECT id, username FROM accounts;"
```

**Правильный вывод:**
```
      id     |  username
------------+------------
  25025320   | instagram
  123456789  | some_account
```

**Неправильный вывод (если ID маленькие - переделать!):**
```
 id |  username
----+------------
  1  | instagram
  2  | some_account
```

---

## Быстрый старт деплоя

### 1. Подготовка сервера

```bash
# Установить Docker (если нет)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo apt install docker-compose-plugin -y

# Добавить пользователя в группу docker
sudo usermod -aG docker $USER
newgrp docker
```

### 2. Настроить проект

```bash
# Клонировать/скопировать проект
cd /opt/video_stats

# Создать .env из примера
cp .env.example .env
nano .env  # отредактировать

# Создать директории
mkdir -p audio logs cookies
```

### 3. Настроить PostgreSQL

```bash
sudo -u postgres psql
CREATE DATABASE instagram_tracker;
CREATE USER tracker_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE instagram_tracker TO tracker_user;
\q
```

### 4. Инициализировать аккаунты (ВАЖНО!)

```bash
# Запустить миграции
docker compose run --rm admin alembic upgrade head

# Инициализировать аккаунты с правильным user_pk
docker compose run --rm admin python scripts/init_accounts.py user_pks.json

# Проверить, что ID правильные (большие числа, не 1,2,3...)
docker compose exec admin psql ${DATABASE_URL} -c "SELECT id, username FROM accounts;"
```

### 5. Запустить

```bash
# Собрать образы
docker compose build

# Запустить контейнеры
docker compose up -d

# Проверить статус
docker compose ps

# Посмотреть логи
docker compose logs -f
```

---

## Полезные команды

```bash
# Статус контейнеров
docker compose ps

# Логи
docker compose logs -f              # Все сервисы
docker compose logs -f admin        # Только админка
docker compose logs -f worker       # Только воркер

# Перезапуск
docker compose restart admin
docker compose restart worker

# Остановка
docker compose stop
docker compose down

# Пересборка после изменений
docker compose up -d --build
```

---

## Доступ

- Админ-панель: `http://your-server-ip:8000`
- Dashboard: `http://your-server-ip:8000/dashboard`
- Accounts: `http://your-server-ip:8000/accounts`
- JSON Import: `http://your-server-ip:8000/accounts/json-import`

---

## Документация

Подробная информация на английском:
- `DEPLOYMENT.md` - полное руководство по деплою
- `ACCOUNT_INIT_GUIDE.md` - инициализация аккаунтов
- `DEPLOYMENT_CHECKLIST.md` - чеклист проверки

---

## Troubleshooting

### Проблема: Контейнеры не подключаются к PostgreSQL

**Решение:** Использовать `host.docker.internal` для Linux в `DATABASE_URL`

### Проблема: Воркер не запускается

**Проверить:**
```bash
docker compose logs worker
docker compose exec worker env | grep INSTAGRAM
```

### Проблема: Аккаунты с неправильными ID

**Решение:**
```bash
docker compose exec admin psql ${DATABASE_URL} -c "DELETE FROM accounts;"
docker compose run --rm admin python scripts/init_accounts.py user_pks.json
```

### Проблема: Большой размер образа

**Решение:** Использовать CPU-only PyTorch (см. раздел про Whisper выше)

---

## Файлы для деплоя

Все необходимые файлы созданы и готовы к использованию. Проверьте по чеклисту `DEPLOYMENT_CHECKLIST.md`.

Удачного деплоя! 🚀
