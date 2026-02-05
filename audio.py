import yt_dlp
import whisper
import os
import sys
import json


def get_reel_data(url: str):
    """
    Скачивает аудио из видео по URL, получает ссылку на скачивание видео,
    делает транскрипцию аудио и сохраняет всю метадату в JSON.
    """
    audio_filename = "downloaded_audio.mp3"
    info_dict = None
    whisper_result = None
    video_url = None

    # --- 1. Получение информации и скачивание аудио с помощью yt-dlp ---
    try:
        # Настройки для скачивания только аудио в формате mp3
        ydl_audio_opts = {
            'format': 'bestaudio/best',
            'outtmpl': audio_filename.split('.')[0],  # Имя файла без расширения
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
            'noprogress': True,
        }

        print("Шаг 1/3: Скачивание аудио...")
        with yt_dlp.YoutubeDL(ydl_audio_opts) as ydl:
            ydl.download([url])

        if not os.path.exists(audio_filename):
            raise FileNotFoundError(
                "Не удалось скачать аудиофайл. Проверьте ссылку или настройки yt-dlp."
            )

        # Настройки для получения полной метадаты и прямой ссылки на видео
        ydl_video_opts = {'quiet': True, 'noprogress': True}
        with yt_dlp.YoutubeDL(ydl_video_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            video_url = info_dict.get('url')

    except Exception as e:
        print(f"\n[ОШИБКА] Не удалось обработать ссылку с помощью yt-dlp: {e}")
        print("Убедитесь, что ссылка верна и yt-dlp может получить к ней доступ.")
        if os.path.exists(audio_filename):
            os.remove(audio_filename)
        sys.exit(1)

    # --- 2. Транскрипция аудио с помощью Whisper ---
    try:
        print("Шаг 2/3: Загрузка модели Whisper (может занять время при первом запуске)...")
        model = whisper.load_model("base")

        print("Шаг 3/3: Транскрибация аудио...")
        whisper_result = model.transcribe(audio_filename, fp16=False)
        transcription = whisper_result.get('text', '')

    except Exception as e:
        print(f"\n[ОШИБКА] Произошла ошибка во время транскрибации: {e}")
        sys.exit(1)

    # --- 3. Сохранение всей метадаты в JSON ---
    metadata = {
        "source_url": url,
        "video_url": video_url,
        "audio_filename": audio_filename,
        "yt_dlp_info": info_dict,
        "whisper_result": whisper_result,
    }

    output_json = "metadata.json"
    try:
        with open(output_json, "w", encoding="utf-8") as f:
            # default=str на случай нестандартных типов (numpy и т.п.)
            json.dump(metadata, f, ensure_ascii=False, indent=2, default=str)
        print(f"\nМетаданные сохранены в файл: {output_json}")
    except Exception as e:
        print(f"\n[ОШИБКА] Не удалось сохранить метаданные в JSON: {e}")

    # --- 4. Краткий вывод в консоль (по желанию) ---
    print("\n" + "=" * 50)
    print("                РЕЗУЛЬТАТЫ")
    print("=" * 50 + "\n")

    print("🔗 Ссылка для скачивания видео:")
    print(video_url if video_url else "Не удалось получить ссылку на видео.")

    print("\n" + "-" * 50 + "\n")

    print("📜 Транскрипция текста:")
    print(transcription if transcription else "Текст не распознан.")
    print("\n" + "=" * 50)


if __name__ == "__main__":
    reel_url = input("Введите ссылку на Instagram Reel и нажмите Enter: ")
    if reel_url:
        get_reel_data(reel_url)
    else:
        print("Ссылка не была введена. Завершение работы.")