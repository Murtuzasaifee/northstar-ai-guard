from llm_guard import scan_prompt, scan_output
from llm_guard.input_scanners import Toxicity, PromptInjection, BanTopics
from llm_guard.output_scanners import (
    Toxicity as OutputToxicity,
    Sensitive,
    NoRefusal,
    BanTopics as OutputBanTopics,
)


_input_moderation_scanners = None
_output_moderation_scanners = None


def _get_input_moderation_scanners():
    global _input_moderation_scanners
    if _input_moderation_scanners is None:
        _input_moderation_scanners = [
            Toxicity(threshold=0.5),
            BanTopics(topics=["violence", "self-harm", "hate speech", "illegal drugs"]),
        ]
    return _input_moderation_scanners


def _get_output_moderation_scanners():
    global _output_moderation_scanners
    if _output_moderation_scanners is None:
        _output_moderation_scanners = [
            OutputToxicity(threshold=0.5),
            Sensitive(redact=True),
            OutputBanTopics(topics=["violence", "self-harm", "hate speech"]),
        ]
    return _output_moderation_scanners


def moderate_input(text: str) -> tuple[bool, str, list[str]]:
    scanners = _get_input_moderation_scanners()
    sanitized, results_valid, results_score = scan_prompt(scanners, text)

    is_safe = all(results_valid.values())
    violations = [
        f"{name} (score: {results_score[name]:.2f})"
        for name, passed in results_valid.items()
        if not passed
    ]

    return is_safe, sanitized, violations


def moderate_output(output: str, prompt: str) -> tuple[bool, str, list[str]]:
    scanners = _get_output_moderation_scanners()
    sanitized, results_valid, results_score = scan_output(scanners, prompt, output)

    is_safe = all(results_valid.values())
    violations = [
        f"{name} (score: {results_score[name]:.2f})"
        for name, passed in results_valid.items()
        if not passed
    ]

    return is_safe, sanitized, violations
