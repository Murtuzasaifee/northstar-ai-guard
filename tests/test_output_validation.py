import pytest
from pydantic import ValidationError

from app.security.output_validator import (
    validate_llm_output,
    validate_with_retry,
    OutputValidationError,
)


class TestOutputValidation:
    def test_valid_json_output(self):
        raw = '{"answer": "You get 20 days leave.", "sources": ["hr_policy.txt"], "confidence": 0.9, "tokens_used": 50}'
        result = validate_llm_output(raw)
        assert result.answer == "You get 20 days leave."
        assert result.confidence == 0.9

    def test_json_in_code_block(self):
        raw = '```json\n{"answer": "Yes", "sources": [], "confidence": 0.8, "tokens_used": 10}\n```'
        result = validate_llm_output(raw)
        assert result.answer == "Yes"

    def test_json_in_plain_code_block(self):
        raw = '```\n{"answer": "Yes", "sources": [], "confidence": 0.8, "tokens_used": 10}\n```'
        result = validate_llm_output(raw)
        assert result.answer == "Yes"

    def test_invalid_json_raises(self):
        with pytest.raises(OutputValidationError, match="invalid JSON"):
            validate_llm_output("this is not json")

    def test_missing_fields_raises(self):
        with pytest.raises(OutputValidationError, match="schema"):
            validate_llm_output('{"answer": "Yes"}')

    def test_invalid_confidence_raises(self):
        with pytest.raises(OutputValidationError):
            validate_llm_output(
                '{"answer": "Yes", "sources": [], "confidence": 5.0, "tokens_used": 10}'
            )

    def test_validate_with_retry_succeeds_first_attempt(self):
        raw = '{"answer": "Test", "sources": [], "confidence": 0.5, "tokens_used": 5}'
        result, attempts = validate_with_retry(raw)
        assert result.answer == "Test"
        assert attempts == 1

    def test_validate_with_retry_fails_all_attempts(self):
        with pytest.raises(OutputValidationError):
            validate_with_retry("bad json", max_retries=2)

    def test_whitespace_handling(self):
        raw = '  \n  {"answer": "Trimmed", "sources": ["a.txt"], "confidence": 0.7, "tokens_used": 20}  \n  '
        result = validate_llm_output(raw)
        assert result.answer == "Trimmed"
