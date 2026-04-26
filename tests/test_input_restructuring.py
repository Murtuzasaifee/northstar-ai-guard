import pytest

from app.security.input_restructuring import count_tokens, restructure_input


class TestInputRestructuring:
    def test_count_tokens_short(self):
        assert count_tokens("Hello world") > 0

    def test_count_tokens_empty(self):
        assert count_tokens("") == 0

    def test_short_message_unchanged(self):
        msg = "What is the leave policy?"
        result, method = restructure_input(msg)
        assert result == msg
        assert method == "original"

    def test_medium_message_truncated(self):
        msg = "word " * 5000
        result, method = restructure_input(msg, max_tokens=1000, context_tokens=100)
        assert method in ("truncated", "summarized")
        assert len(result) < len(msg)
        assert "[Message was" in result

    def test_long_message_summarized(self):
        sentences = []
        for i in range(200):
            sentences.append(
                f"Sentence number {i} about company policies at Northstar Dynamics."
            )
        msg = ". ".join(sentences)
        result, method = restructure_input(msg, max_tokens=500, context_tokens=100)
        assert method == "summarized"
        assert len(result) < len(msg)
        assert "[Message was summarized" in result

    def test_context_tokens_reserved(self):
        msg = "a " * 2000
        result, method = restructure_input(msg, max_tokens=100, context_tokens=50)
        assert count_tokens(result) < 100

    def test_preserves_content_for_short_input(self):
        msg = "How many sick days do I get?"
        result, method = restructure_input(msg)
        assert "sick days" in result
        assert method == "original"
