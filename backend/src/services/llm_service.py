import time
import httpx
from loguru import logger
from typing import Optional

from src.settings import settings
from src.schemas.chat import ChatMessage
from src.middleware.request_id import request_id_ctx

# ============================================
# CONSTANTS
# ============================================
OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"

# Статический fallback-список (на случай, если API OpenRouter недоступен)
FALLBACK_MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "qwen/qwen-2.5-7b-instruct:free",
    "google/gemma-3-1b-it:free",
    "mistralai/mistral-small-3.1-24b-instruct:free",
    "deepseek/deepseek-chat-v3-0324:free",
]

SYSTEM_PROMPT = (
    "Ты — корпоративный ассистент заказа такси. "
    "Отвечай коротко, вежливо, по-русски. "
    "На первое сообщение пользователя отвечай приветствием и вопросом 'Куда поедем?'. "
    "Не выдумывай адреса, не давай маршруты — этим занимается карта."
)


# ============================================
# DYNAMIC FREE MODELS CACHE
# ============================================
_free_models_cache: list[str] = []
_last_models_fetch: float = 0.0


async def get_available_free_models() -> list[str]:
    """
    Получает актуальный список бесплатных моделей с OpenRouter API.

    Логика полностью из Flask-проекта:
    - Кэш на 1 час (OPENROUTER_MODELS_CACHE_TTL)
    - Фильтрация по :free или pricing=="0"
    - Проверка context_length > 0
    - Fallback на статический список при ошибке API
    """
    global _free_models_cache, _last_models_fetch

    request_id = request_id_ctx.get()

    # Возвращаем кэш, если он свежий
    cache_age = time.time() - _last_models_fetch
    if cache_age < settings.OPENROUTER_MODELS_CACHE_TTL and _free_models_cache:
        logger.debug(
            "📦 Using cached free models",
            extra={
                "request_id": request_id,
                "cache_age": round(cache_age, 1),
                "count": len(_free_models_cache),
            },
        )
        return _free_models_cache

    # Обновляем кэш
    logger.info(
        "🔄 Fetching fresh free models from OpenRouter",
        extra={
            "request_id": request_id,
        },
    )

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                OPENROUTER_MODELS_URL,
                headers={"Authorization": f"Bearer {settings.OPENROUTER_API_KEY}"},
            )
            response.raise_for_status()
            data = response.json()

        models_data = data.get("data", [])
        logger.info(
            f"📊 Total models in OpenRouter catalog: {len(models_data)}",
            extra={
                "request_id": request_id,
            },
        )

        # Фильтруем бесплатные модели
        free_models: list[str] = []
        for m in models_data:
            model_id = m.get("id", "")
            pricing = m.get("pricing", {})

            # ВАЖНО: цены приходят СТРОКАМИ ("0"), не числами
            is_free = model_id.endswith(":free") or (
                pricing.get("prompt") == "0" and pricing.get("completion") == "0"
            )

            # Модель должна быть активной
            has_context = m.get("context_length", 0) > 0

            if is_free and has_context:
                free_models.append(model_id)

        # Берём топ-N моделей
        result = free_models[: settings.OPENROUTER_MAX_MODELS]

        if result:
            _free_models_cache = result
            _last_models_fetch = time.time()
            logger.info(
                f"✅ Found {len(result)} free models:",
                extra={
                    "request_id": request_id,
                    "models": result,
                },
            )
            return result
        else:
            logger.warning(
                "⚠️ No free models found, using fallback",
                extra={
                    "request_id": request_id,
                },
            )
            _free_models_cache = FALLBACK_MODELS
            _last_models_fetch = time.time()
            return FALLBACK_MODELS

    except Exception as e:
        logger.warning(
            f"⚠️ Failed to fetch models from OpenRouter: {e}",
            extra={
                "request_id": request_id,
            },
        )
        _free_models_cache = FALLBACK_MODELS
        _last_models_fetch = time.time()
        return FALLBACK_MODELS


def invalidate_models_cache():
    """Принудительная инвалидация кэша (для эндпоинта /models/refresh)."""
    global _free_models_cache, _last_models_fetch
    _free_models_cache = []
    _last_models_fetch = 0.0


# ============================================
# SINGLE MODEL CALL
# ============================================
async def _try_call_model(
    client: httpx.AsyncClient,
    model: str,
    messages: list[dict],
) -> str:
    """Попытка вызова конкретной модели."""
    response = await client.post(
        OPENROUTER_CHAT_URL,
        headers={
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://taxi-agent.local",
            "X-Title": "Taxi Agent",
        },
        json={
            "model": model,
            "messages": messages,
            "temperature": 0.4,
            "max_tokens": 200,
        },
        timeout=settings.OPENROUTER_TIMEOUT,
    )

    if response.status_code == 429:
        raise httpx.HTTPStatusError(
            "Rate limited", request=response.request, response=response
        )
    if response.status_code == 404:
        raise httpx.HTTPStatusError(
            "Model not found", request=response.request, response=response
        )

    response.raise_for_status()
    data = response.json()

    # OpenRouter иногда возвращает 200 с ошибкой в теле
    if "error" in data:
        raise ValueError(f"Model error: {data['error'].get('message', 'unknown')}")

    return data["choices"][0]["message"]["content"]


# ============================================
# MAIN CHAT FUNCTION
# ============================================
async def chat_with_agent(message: str, history: list[ChatMessage]) -> str:
    """
    Чат с LLM через OpenRouter с:
    - Динамическим кэшем бесплатных моделей
    - Fallback на каждую следующую модель при ошибке
    - Fallback-сообщением если все модели отказали
    """
    request_id = request_id_ctx.get()

    # Формируем messages
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(
        [{"role": msg.role, "content": msg.content} for msg in history[-10:]]
    )
    messages.append({"role": "user", "content": message})

    logger.info(
        "🤖 Starting LLM call",
        extra={
            "request_id": request_id,
            "message_length": len(message),
        },
    )

    # Получаем актуальный список моделей (из кэша или API)
    models_to_try = await get_available_free_models()

    async with httpx.AsyncClient() as client:
        for model in models_to_try:
            logger.debug(
                f"🔄 Trying model: {model}",
                extra={
                    "request_id": request_id,
                },
            )

            try:
                reply = await _try_call_model(client, model, messages)

                logger.info(
                    f"✅ Success from '{model}'",
                    extra={
                        "request_id": request_id,
                        "model": model,
                        "reply_length": len(reply),
                    },
                )
                return reply

            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                logger.warning(
                    f"⏱️ Model '{model}' returned {status}, trying next",
                    extra={"request_id": request_id, "model": model, "status": status},
                )
                continue

            except httpx.TimeoutException:
                logger.warning(
                    f"⏱️ Timeout for '{model}', trying next",
                    extra={"request_id": request_id, "model": model},
                )
                continue

            except (httpx.ConnectError, ValueError) as e:
                logger.warning(
                    f"💥 Error for '{model}': {type(e).__name__}, trying next",
                    extra={"request_id": request_id, "model": model, "error": str(e)},
                )
                continue

            except Exception as e:
                logger.error(
                    f"❌ Unexpected error for '{model}': {e}",
                    extra={
                        "request_id": request_id,
                        "model": model,
                    },
                )
                continue

    # Все модели отказали
    logger.error(
        "❌ ALL MODELS FAILED",
        extra={
            "request_id": request_id,
            "models_tried": len(models_to_try),
        },
    )
    return "Извините, все AI-модели сейчас перегружены. Попробуйте через минуту."
