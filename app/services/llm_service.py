import json
import logging

from openai import OpenAI

from app.config import settings
from app.rag.spotlighting import build_spotlighted_context
from app.security.input_guard import scan_input
from app.security.content_moderation import moderate_input, moderate_output
from app.security.input_restructuring import restructure_input, count_tokens
from app.security.output_validator import validate_with_retry
from app.security.system_prompt import get_system_prompt_with_context
from app.models.request import ChatResponse

logger = logging.getLogger(__name__)

_client = None


def _get_openai_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=settings.openai_api_key)
    return _client


def process_chat(user_id: str, message: str) -> dict:
    restructured_msg, method = restructure_input(message)
    logger.info(f"Input restructured via: {method}")

    input_tokens = count_tokens(restructured_msg)
    logger.info(f"Input token count: {input_tokens}")

    is_safe, sanitized, failed_checks, scores = scan_input(restructured_msg)
    if not is_safe:
        logger.warning(f"LLM Guard blocked input: {failed_checks}, scores: {scores}")
        return {
            "blocked": True,
            "reason": "semantic_threat",
            "details": f"Blocked by: {', '.join(failed_checks)}",
            "scores": scores,
        }

    input_safe, input_sanitized, input_violations = moderate_input(sanitized)
    if not input_safe:
        logger.warning(f"Input moderation blocked: {input_violations}")
        return {
            "blocked": True,
            "reason": "content_moderation_input",
            "details": f"Input violations: {', '.join(input_violations)}",
        }

    context, source_names = build_spotlighted_context(sanitized)
    system_prompt = get_system_prompt_with_context(context)

    client = _get_openai_client()
    completion = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": sanitized},
        ],
        max_completion_tokens=1000,
    )

    raw_output = completion.choices[0].message.content or ""
    output_tokens = completion.usage.total_tokens if completion.usage else 0

    output_safe, output_sanitized, output_violations = moderate_output(
        raw_output, sanitized
    )
    if not output_safe:
        logger.warning(f"Output moderation blocked: {output_violations}")
        return {
            "blocked": True,
            "reason": "content_moderation_output",
            "details": f"Output violations: {', '.join(output_violations)}",
        }

    try:
        validated_response, attempts = validate_with_retry(
            output_sanitized, max_retries=settings.max_retries
        )
    except Exception as e:
        logger.error(f"Output validation failed after retries: {e}")
        return {
            "blocked": True,
            "reason": "output_validation",
            "details": str(e),
        }

    return {
        "blocked": False,
        "response": validated_response.model_dump(),
        "tokens_used": output_tokens,
        "input_method": method,
        "validation_attempts": attempts,
    }
