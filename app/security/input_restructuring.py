import tiktoken

from app.config import settings

_encoding = None


def _get_encoding():
    global _encoding
    if _encoding is None:
        try:
            _encoding = tiktoken.encoding_for_model(settings.openai_model)
        except KeyError:
            _encoding = tiktoken.get_encoding("cl100k_base")
    return _encoding


def count_tokens(text: str) -> int:
    enc = _get_encoding()
    return len(enc.encode(text))


def restructure_input(
    message: str,
    max_tokens: int = 3000,
    context_tokens: int = 1000,
) -> tuple[str, str]:
    input_tokens = count_tokens(message)
    available_tokens = max_tokens - context_tokens

    if input_tokens <= available_tokens:
        return message, "original"

    if input_tokens <= available_tokens * 2:
        truncated = _truncate_to_tokens(message, available_tokens)
        return truncated, "truncated"

    summary = _summarize_by_sentences(message, available_tokens)
    return summary, "summarized"


def _truncate_to_tokens(text: str, max_tokens: int) -> str:
    enc = _get_encoding()
    tokens = enc.encode(text)
    truncated_tokens = tokens[:max_tokens]
    decoded = enc.decode(truncated_tokens)
    return decoded + "\n\n[Message was truncated due to length]"


def _summarize_by_sentences(text: str, max_tokens: int) -> str:
    sentences = text.replace("!", ".").replace("?", ".").split(".")
    sentences = [s.strip() for s in sentences if s.strip()]

    enc = _get_encoding()
    kept = []
    token_count = 0

    for sentence in sentences:
        sentence_tokens = len(enc.encode(sentence))
        if token_count + sentence_tokens <= max_tokens:
            kept.append(sentence)
            token_count += sentence_tokens
        else:
            break

    result = ". ".join(kept)
    if not result.endswith("."):
        result += "."

    return result + "\n\n[Message was summarized due to excessive length]"
