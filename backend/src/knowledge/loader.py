import json
from pathlib import Path
from loguru import logger

KNOWLEDGE_PATH = Path(__file__).parent / "taxi_faq.json"


def load_knowledge() -> dict:
    """Загружает базу знаний из JSON"""
    if not KNOWLEDGE_PATH.exists():
        logger.warning(f"⚠️ База знаний не найдена: {KNOWLEDGE_PATH}")
        return {}

    with open(KNOWLEDGE_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    logger.info(f"✅ База знаний загружена: {len(data.get('faq', []))} FAQ")
    return data


def build_system_prompt(knowledge: dict) -> str:
    """Формирует системный промпт на основе базы знаний"""
    if not knowledge:
        return "Ты — умный помощник такси-агента. Отвечай кратко и по делу на русском языке."

    company = knowledge.get("company", {})
    tariffs = knowledge.get("tariffs", {})
    faq = knowledge.get("faq", [])
    behavior = knowledge.get("agent_behavior", {})

    # Тарифы в читаемом виде
    tariffs_text = "\n".join(
        [
            f"- {t['name']}: от {t['min_price']}₽, {t['price_per_km']}₽/км, {t['price_per_min']}₽/мин. {t['description']}"
            for t in tariffs.values()
        ]
    )

    # FAQ
    faq_text = "\n".join(
        [f"В: {item['question']}\nО: {item['answer']}" for item in faq]
    )

    # Правила поведения
    rules_text = "\n".join([f"- {rule}" for rule in behavior.get("rules", [])])

    prompt = f"""Ты — {company.get('name', 'Такси-агент')}. {company.get('description', '')}.
Зона обслуживания: {company.get('service_area', 'Россия')}.
Телефон поддержки: {company.get('support_phone', 'не указан')}.
Email поддержки: {company.get('support_email', 'не указан')}.

## Тарифы:
{tariffs_text}

## Частые вопросы и ответы:
{faq_text}

## Правила поведения:
{rules_text}

Отвечай ТОЛЬКО на основе этой информации. Если вопрос выходит за рамки — вежливо предложи связаться с поддержкой."""

    return prompt


# Кэш
_knowledge_cache = None
_system_prompt_cache = None


def get_knowledge() -> dict:
    global _knowledge_cache
    if _knowledge_cache is None:
        _knowledge_cache = load_knowledge()
    return _knowledge_cache


def get_system_prompt() -> str:
    global _system_prompt_cache
    if _system_prompt_cache is None:
        _system_prompt_cache = build_system_prompt(get_knowledge())
    return _system_prompt_cache


def reload_knowledge():
    """Перезагрузка базы знаний без рестарта"""
    global _knowledge_cache, _system_prompt_cache
    _knowledge_cache = load_knowledge()
    _system_prompt_cache = build_system_prompt(_knowledge_cache)
    logger.info("🔄 База знаний перезагружена")
