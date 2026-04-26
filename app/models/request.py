import re

from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="User message to the AI assistant",
    )

    @field_validator("message")
    @classmethod
    def validate_message_content(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Message cannot be empty or whitespace only")

        injection_patterns = [
            r"(?i)(ignore\s+previous|ignore\s+above|forget\s+your\s+instructions)",
            r"(?i)(system\s*prompt|reveal\s+your\s+instructions|show\s+your\s+prompt)",
            r"(?i)(you\s+are\s+now|new\s+instructions|override\s+previous)",
            r"(?i)(<\s*script|javascript:|on\w+\s*=)",
        ]
        for pattern in injection_patterns:
            if re.search(pattern, v):
                raise ValueError("Message contains potentially malicious content")

        if re.match(r"^[\W_]+$", v):
            raise ValueError("Message must contain actual text content")

        return v


class ChatResponse(BaseModel):
    answer: str = Field(..., min_length=1, description="The assistant's answer")
    sources: list[str] = Field(
        default_factory=list, description="Document sources used for the answer"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score between 0 and 1"
    )
    tokens_used: int = Field(
        default=0, ge=0, description="Token count associated with the response"
    )
