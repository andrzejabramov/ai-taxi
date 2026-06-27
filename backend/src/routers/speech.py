from fastapi import APIRouter, UploadFile, File, HTTPException
from loguru import logger
import httpx

from src.settings import settings

router = APIRouter(prefix="/speech", tags=["speech"])


@router.post("/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    """
    Транскрибация аудио через Yandex SpeechKit.
    Используется как fallback для браузеров без Web Speech API (Firefox).
    """
    if not settings.YANDEX_SPEECHKIT_API_KEY:
        raise HTTPException(
            status_code=500, detail="YANDEX_SPEECHKIT_API_KEY not configured in .env"
        )

    # Читаем аудио
    content = await audio.read()

    # Определяем формат по content-type
    content_type = audio.content_type or "audio/webm"

    # Маппинг форматов для SpeechKit
    format_map = {
        "webm": "webm",
        "audio/webm": "webm",
        "ogg": "oggopus",
        "audio/ogg": "oggopus",
        "wav": "lpcm",
        "audio/wav": "lpcm",
        "audio/wave": "lpcm",
    }

    format_hint = format_map.get(content_type, "webm")

    # Формируем параметры запроса
    params = {
        "topic": "general",
        "lang": "ru-RU",
        "format": format_hint,
    }

    # Для LPCM (WAV) нужен sampleRateHertz
    if format_hint == "lpcm":
        params["sampleRateHertz"] = 16000

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize",
                headers={
                    "Authorization": f"Api-Key {settings.YANDEX_SPEECHKIT_API_KEY}",
                },
                params=params,
                content=content,
            )

            if response.status_code != 200:
                logger.error(f"SpeechKit error: {response.status_code} {response.text}")
                raise HTTPException(
                    status_code=500, detail=f"Transcription failed: {response.text}"
                )

            result = response.json()
            text = result.get("result", "")

            logger.info(f"✅ Audio transcribed (Yandex SpeechKit): '{text[:50]}'")

            return {
                "text": text,
                "language": "ru",
                "provider": "yandex-speechkit",
            }

    except httpx.HTTPStatusError as e:
        logger.error(
            f"SpeechKit HTTP error: {e.response.status_code} {e.response.text}"
        )
        raise HTTPException(
            status_code=500, detail=f"Transcription failed: {e.response.text}"
        )
    except Exception as e:
        logger.error(f"SpeechKit error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
