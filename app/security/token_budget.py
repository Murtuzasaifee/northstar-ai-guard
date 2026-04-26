import datetime

from app.middleware.rate_limiter import get_redis_client
from app.config import settings


class TokenBudget:
    def __init__(self, max_tokens_daily: int):
        self.max_tokens_daily = max_tokens_daily

    def get_usage(self, user_id: str) -> dict:
        client = get_redis_client()
        key = self._key(user_id)
        used = int(client.get(key) or 0)
        return {
            "used": used,
            "limit": self.max_tokens_daily,
            "remaining": max(0, self.max_tokens_daily - used),
            "percentage": round((used / self.max_tokens_daily) * 100, 2),
        }

    def check_budget(self, user_id: str, estimated_tokens: int = 0) -> bool:
        usage = self.get_usage(user_id)
        return (usage["remaining"] - estimated_tokens) > 0

    def consume(self, user_id: str, tokens: int) -> dict:
        client = get_redis_client()
        key = self._key(user_id)
        pipe = client.pipeline()
        pipe.incrby(key, tokens)
        pipe.expire(key, self._seconds_until_midnight())
        results = pipe.execute()
        used = results[0]
        return {
            "used": used,
            "limit": self.max_tokens_daily,
            "remaining": max(0, self.max_tokens_daily - used),
            "tokens_charged": tokens,
        }

    def _key(self, user_id: str) -> str:
        today = datetime.date.today().isoformat()
        return f"token_budget:{user_id}:{today}"

    def _seconds_until_midnight(self) -> int:
        now = datetime.datetime.now()
        tomorrow = now + datetime.timedelta(days=1)
        midnight = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
        return int((midnight - now).total_seconds())


token_budget = TokenBudget(max_tokens_daily=settings.max_tokens_per_user_daily)
