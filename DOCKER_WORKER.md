# Docker Worker - Quick Start

## Сборка образа

```bash
docker build -f Dockerfile.worker -t video-stats-worker .
```

## Запуск с прокси

### Пример с SOCKS5 прокси

```bash
docker run -d \
  --name video_stats_worker \
  --restart unless-stopped \
  -e DATABASE_URL="postgresql+asyncpg://user:password@db_host:5432/dbname" \
  -e INSTAGRAM_USERNAME="your_username" \
  -e INSTAGRAM_PASSWORD="your_password" \
  -e INSTAGRAM_PROXY="socks5h://user:password@proxy_host:port" \
  -e WORKER_INTERVAL_HOURS=24 \
  -v $(pwd)/audio:/app/audio \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/instagram_settings.json:/app/instagram_settings.json \
  video-stats-worker
```

### Пример с HTTP прокси

```bash
docker run -d \
  --name video_stats_worker \
  --restart unless-stopped \
  -e DATABASE_URL="postgresql+asyncpg://user:password@db_host:5432/dbname" \
  -e INSTAGRAM_USERNAME="your_username" \
  -e INSTAGRAM_PASSWORD="your_password" \
  -e INSTAGRAM_PROXY="http://user:password@proxy_host:port" \
  -e WORKER_INTERVAL_HOURS=24 \
  -v $(pwd)/audio:/app/audio \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/instagram_settings.json:/app/instagram_settings.json \
  video-stats-worker
```

### Без прокси

Просто не указывайте `INSTAGRAM_PROXY` или оставьте пустым:

```bash
docker run -d \
  --name video_stats_worker \
  --restart unless-stopped \
  -e DATABASE_URL="postgresql+asyncpg://user:password@db_host:5432/dbname" \
  -e INSTAGRAM_USERNAME="your_username" \
  -e INSTAGRAM_PASSWORD="your_password" \
  -e INSTAGRAM_PROXY="" \
  -e WORKER_INTERVAL_HOURS=24 \
  -v $(pwd)/audio:/app/audio \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/instagram_settings.json:/app/instagram_settings.json \
  video-stats-worker
```

## Использование .env файла

Создайте `.env` файл:

```bash
DATABASE_URL=postgresql+asyncpg://user:password@db_host:5432/dbname
INSTAGRAM_USERNAME=your_username
INSTAGRAM_PASSWORD=your_password
INSTAGRAM_PROXY=socks5h://user:password@proxy_host:port
WORKER_INTERVAL_HOURS=24
TEST_MODE=false
```

Запустите контейнер:

```bash
docker run -d \
  --name video_stats_worker \
  --restart unless-stopped \
  --env-file .env \
  -v $(pwd)/audio:/app/audio \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/instagram_settings.json:/app/instagram_settings.json \
  video-stats-worker
```

## Поддерживаемые форматы прокси

- **HTTP**: `http://user:password@host:port`
- **HTTPS**: `https://user:password@host:port`
- **SOCKS5**: `socks5://user:password@host:port`
- **SOCKS5 with DNS**: `socks5h://user:password@host:port` (рекомендуется для Instagram)

## Просмотр логов

```bash
# Все логи
docker logs -f video_stats_worker

# Последние 100 строк
docker logs --tail 100 video_stats_worker
```

## Остановка и перезапуск

```bash
# Остановить
docker stop video_stats_worker

# Запустить снова
docker start video_stats_worker

# Удалить контейнер
docker rm -f video_stats_worker
```

## Важные замечания

### ⚠️ Прокси работает ТОЛЬКО для instagrapi

- ✅ **Instagram API запросы** (вход, получение видео, метрик) - используют прокси
- ❌ **yt-dlp** (скачивание аудио) - НЕ использует прокси (не требуется для Instagram)

### 💡 Рекомендации по прокси

1. **Используйте SOCKS5h** (обратите внимание на `h` в конце) - это самый надежный формат для Instagram
2. **Используйте вращающиеся прокси** если планируете много запросов
3. **Проверяйте прокси** перед использованием:
   ```bash
   curl --socks5-hostname user:password@proxy_host:port https://www.instagram.com
   ```

### 📁 Vol mounts (сохранение данных)

- `/app/audio` - скачанные аудиофайлы
- `/app/logs` - логи приложения
- `/app/instagram_settings.json` - сессия Instagram (сохраняется между перезапусками)

## Troubleshooting

### Прокси не работает

Проверьте логи:
```bash
docker logs video_stats_worker | grep -i proxy
```

Должно быть:
```
Configured proxy: socks5h://user:password@proxy_host:port
```

Если видите:
```
Failed to set proxy: ...
```
- Проверьте формат прокси
- Убедитесь, что прокси доступен из контейнера
- Попробуйте другой формат (socks5:// вместо socks5h://)

### Ошибка аутентификации

1. Проверьте `INSTAGRAM_USERNAME` и `INSTAGRAM_PASSWORD`
2. Убедитесь, что прокси работает (если используется)
3. Проверьте файл `instagram_settings.json` - удалите его и перезапустите контейнер

### Whisper не работает

Whisper использует CPU версию PyTorch (уже установлена в Dockerfile).
Если проблемы с памятью, ограничьте ресурсы контейнера:
```bash
docker run -d \
  ...
  --memory="2g" \
  --cpus="2" \
  video-stats-worker
```
