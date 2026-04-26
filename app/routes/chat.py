import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.middleware.auth import get_current_user
from app.middleware.rate_limiter import rate_limiter
from app.models.request import ChatRequest, ChatResponse
from app.security.token_budget import token_budget
from app.security.input_restructuring import count_tokens
from app.services.llm_service import process_chat

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/", response_model=dict)
def chat(
    req: ChatRequest,
    current_user: dict = Depends(get_current_user),
):
    username = current_user["username"]

    # Feature 4: Rate Limiting
    allowed, remaining, request_count = rate_limiter.is_allowed(username)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded",
                "limit": rate_limiter.max_requests,
                "window_seconds": rate_limiter.window_seconds,
                "retry_after": rate_limiter.window_seconds,
            },
        )

    # Feature 6: Token Budget
    estimated_tokens = count_tokens(req.message) * 3
    if not token_budget.check_budget(username, estimated_tokens):
        usage = token_budget.get_usage(username)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Token budget exceeded",
                "usage": usage,
            },
        )

    # Features 1-3, 5, 7-9: Full security pipeline
    result = process_chat(username, req.message)

    if result.get("blocked"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Request blocked by security layer",
                "reason": result["reason"],
                "details": result["details"],
            },
        )

    # Feature 6: Consume tokens
    if result.get("tokens_used"):
        token_budget.consume(username, result["tokens_used"])

    return result
