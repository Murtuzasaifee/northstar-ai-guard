from llm_guard import scan_prompt
from llm_guard.input_scanners import (
    PromptInjection,
    Toxicity,
    BanTopics,
    TokenLimit,
)


_input_scanners = None


def get_input_scanners(max_tokens: int = 4096):
    global _input_scanners
    if _input_scanners is None:
        _input_scanners = [
            PromptInjection(threshold=0.75),
            Toxicity(threshold=0.75),
            BanTopics(topics=["violence", "self-harm", "illegal activities"]),
            TokenLimit(limit=max_tokens),
        ]
    return _input_scanners


def scan_input(prompt: str) -> tuple[bool, str, list[str]]:
    scanners = get_input_scanners()
    sanitized_prompt, results_valid, results_score = scan_prompt(scanners, prompt)

    is_safe = all(results_valid.values())
    failed_checks = [name for name, passed in results_valid.items() if not passed]
    scores = {
        name: score for name, score in results_score.items() if not results_valid[name]
    }

    return is_safe, sanitized_prompt, failed_checks, scores
