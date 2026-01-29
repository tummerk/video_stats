"""
Простой воркер для Instagram Reels - MVP версия.
Без сервисов, классов и прочего - просто работает.
"""

import asyncio
import logging
from pathlib import Path
from datetime import datetime

import instaloader
import yt_dlp
import whisper
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.config import settings
from src.database import get_session
from src.repositories.account_repository import AccountRepository
from src.repositories.video_repository import VideoRepository

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Глобальные переменные
WHISPER_MODEL = None
INSTA_CLIENT = None
AUDIO_DIR = Path(settings.audio_dir)
AUDIO_DIR.mkdir(parents=True, exist_ok=True)


def get_whisper_model():
    """Загружаем модель один раз."""
    global WHISPER_MODEL
    if WHISPER_MODEL is None:
        logger.info("Загружаю Whisper модель...")
        WHISPER_MODEL = whisper.load_model("base")
    return WHISPER_MODEL


def get_insta_client():
    """Создаём клиент Instagram один раз."""
    global INSTA_CLIENT
    if INSTA_CLIENT is None:
        L = instaloader.Instaloader(
            download_videos=False,
            download_comments=False,
            save_metadata=False
        )
        # Устанавливаем куки
        cookies = {
            "sessionid": "77937472037%3AAw4MCD7pCWtiQM%3A10%3AAYhi8IyqRQqMJP4PIf6iP5BJEVDsqkM4EIrSRX2FyQ",
            "ds_user_id": "77937472037",
            "csrftoken": "zRXlCWjdkAHNbF-bToqNdC",
            "mid": "aXpJDwALAAEmKkf6O0Q-Tf8FfkgG",
        }
        for name, value in cookies.items():
            if value:
                L.context._session.cookies.set(name, value, domain=".instagram.com")
        INSTA_CLIENT = L
        logger.info("Instagram клиент создан")
    return INSTA_CLIENT


def download_audio(url: str, shortcode: str) -> str | None:
    """Скачиваем аудио из рилса. Возвращает путь к файлу."""
    audio_path = AUDIO_DIR / f"{shortcode}.mp3"

    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': str(audio_path.with_suffix('')),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        if audio_path.exists():
            logger.info(f"Скачано аудио: {shortcode}")
            return str(audio_path)
    except Exception as e:
        logger.error(f"Ошибка скачивания {shortcode}: {e}")

    return None


def transcribe_audio(audio_path: str) -> str | None:
    """Транскрибируем аудио."""
    try:
        model = get_whisper_model()
        result = model.transcribe(audio_path, fp16=False)
        logger.info(f"Транскрибировано: {audio_path}")
        return result['text']
    except Exception as e:
        logger.error(f"Ошибка транскрипции {audio_path}: {e}")
        return None


def get_video_url(reel_url: str) -> str | None:
    """Получаем прямую ссылку на видео."""
    try:
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(reel_url, download=False)
            return info.get('url')
    except:
        return None


async def process_account(username: str, account_repo, video_repo) -> int:
    """Обрабатываем один аккаунт. Возвращает кол-во новых видео."""
    processed = 0

    try:
        logger.info(f"Обрабатываю аккаунт: {username}")

        # Получаем профиль
        client = get_insta_client()
        loop = asyncio.get_event_loop()
        profile = await loop.run_in_executor(
            None,
            lambda: instaloader.Profile.from_username(client.context, username)
        )

        # Создаём/обновляем аккаунт в БД
        account = await account_repo.create_or_update_by_username(
            username=username,
            profile_url=f"https://www.instagram.com/{username}/",
            followers_count=profile.followers
        )

        # Получаем рилсы
        reels = profile.get_posts()

        for i, reel in enumerate(reels):
            if reel.i
            if i >= settings.worker_reels_limit:
                logger.info(f"Достигнут лимит {settings.worker_reels_limit} рилсов")
                break

            # Проверяем, есть ли уже в БД
            existing = await video_repo.get_by_shortcode(reel.shortcode)
            if existing:
                logger.info(f"Видео {reel.shortcode} уже есть, пропускаю")
                break

            logger.info(f"Обрабатываю рилс: {reel.shortcode}")

            reel_url = f"https://www.instagram.com/reel/{reel.shortcode}/"

            # Скачиваем и транскрибируем (синхронно в executor)
            audio_path = await loop.run_in_executor(
                None, download_audio, reel_url, reel.shortcode
            )

            transcription = None
            if audio_path:
                transcription = await loop.run_in_executor(
                    None, transcribe_audio, audio_path
                )

            video_url = await loop.run_in_executor(
                None, get_video_url, reel_url
            )

            # Сохраняем в БД
            await video_repo.create_or_update_by_shortcode(
                shortcode=reel.shortcode,
                video_id=reel.video_id,
                video_url=video_url,
                published_at=reel.date_utc,
                caption=reel.caption,
                duration_seconds=reel.video_duration,
                audio_url=video_url,
                audio_file_path=audio_path,
                transcription=transcription,
                account_id=account.id
            )

            processed += 1
            logger.info(f"Сохранён рилс {reel.shortcode}")

            await asyncio.sleep(0.5)  # Небольшая пауза

    except Exception as e:
        logger.error(f"Ошибка обработки {username}: {e}")

    return processed


async def run_job():
    """Основной job - обрабатываем все аккаунты."""
    logger.info("=== Запуск job ===")
    total = 0

    try:
        async with get_session() as session:
            account_repo = AccountRepository(session)
            video_repo = VideoRepository(session)

            accounts = await account_repo.get_all()
            logger.info(f"Найдено аккаунтов: {len(accounts)}")

            for account in accounts:
                count = await process_account(
                    account.username,
                    account_repo,
                    video_repo
                )
                total += count
                await asyncio.sleep(2)  # Пауза между аккаунтами

    except Exception as e:
        logger.error(f"Ошибка в job: {e}")

    logger.info(f"=== Job завершён. Обработано: {total} рилсов ===")


async def main():
    """Точка входа."""
    logger.info("Запуск воркера")
    logger.info(f"Интервал: {settings.worker_interval_hours} часов")
    logger.info(f"Лимит рилсов: {settings.worker_reels_limit}")

    # Создаём планировщик
    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_job, 'interval', hours=settings.worker_interval_hours)
    scheduler.start()

    # Запускаем сразу
    await run_job()

    # Работаем бесконечно
    try:
        await asyncio.Future()
    except KeyboardInterrupt:
        logger.info("Остановка...")
        scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())