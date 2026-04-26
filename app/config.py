import os

os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str = "sk-placeholder"
    openai_model: str = "gpt-5.4-nano"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "change-this-to-a-secure-random-string"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60
    max_input_length: int = 2000
    max_tokens_per_user_daily: int = 100000
    rate_limit_per_minute: int = 20
    chroma_persist_dir: str = "./chroma_data"
    max_retries: int = 2

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
