from fastapi import APIRouter
from loguru import logger

from src.schemas.chat import ChatRequest, ChatResponse
from src.services.llm_service import (
    chat_with_agent,
    get_available_free_models,
    invalidate_models_cache,
)
from src.middleware.request_id import request_id_ctx

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/", response_model=ChatResponse)
async def chat_endpoint(payload: ChatRequest):
    """Чат с LLM-агентом"""
    request_id = request_id_ctx.get()

    logger.info(
        "💬 Chat request",
        extra={
            "request_id": request_id,
            "message_length": len(payload.message),
        },
    )

    reply = await chat_with_agent(payload.message, payload.history)
    return ChatResponse(reply=reply)


@router.get("/models")
async def list_free_models():
    """Актуальный список бесплатных моделей (из кэша или API)"""
    models = await get_available_free_models()
    return {
        "count": len(models),
        "models": models,
        "hint": "Это список, который сейчас используется для fallback-цепочки",
    }


@router.post("/models/refresh")
async def refresh_models_cache():
    """Принудительное обновление кэша моделей"""
    invalidate_models_cache()
    models = await get_available_free_models()
    return {
        "status": "refreshed",
        "count": len(models),
        "models": models,
    }
