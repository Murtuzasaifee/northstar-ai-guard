import json
import logging

from pydantic import ValidationError

from app.models.request import ChatResponse

logger = logging.getLogger(__name__)


class OutputValidationError(Exception):
    def __init__(self, message: str, raw_output: str, attempt: int):
        self.message = message
        self.raw_output = raw_output
        self.attempt = attempt
        super().__init__(message)


def validate_llm_output(raw_output: str, attempt: int = 1) -> ChatResponse:
    try:
        cleaned = raw_output.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        parsed = json.loads(cleaned)
        return ChatResponse(**parsed)

    except json.JSONDecodeError as e:
        logger.warning(
            f"Output validation failed (attempt {attempt}): invalid JSON - {e}"
        )
        raise OutputValidationError(
            f"LLM returned invalid JSON: {e}", raw_output, attempt
        )

    except ValidationError as e:
        logger.warning(
            f"Output validation failed (attempt {attempt}): schema mismatch - {e}"
        )
        raise OutputValidationError(
            f"LLM output doesn't match expected schema: {e}",
            raw_output,
            attempt,
        )


def validate_with_retry(
    raw_output: str, max_retries: int = 2
) -> tuple[ChatResponse, int]:
    attempts = 0
    last_error = None

    for attempt in range(1, max_retries + 1):
        attempts = attempt
        try:
            response = validate_llm_output(raw_output, attempt)
            return response, attempts
        except OutputValidationError as e:
            last_error = e
            if attempt < max_retries:
                logger.info(f"Retrying output validation (attempt {attempt + 1})")

    raise last_error
