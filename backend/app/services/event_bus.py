import json
from typing import Any

from redis import Redis
from redis.exceptions import RedisError

from app.core.config import get_settings


class EventBus:
    def __init__(self) -> None:
        settings = get_settings()
        self._redis_url = settings.redis_url
        self._client: Redis | None = None

    def _get_client(self) -> Redis | None:
        if self._client:
            return self._client
        try:
            self._client = Redis.from_url(self._redis_url, decode_responses=True)
        except RedisError:
            self._client = None
        return self._client

    def publish_company_event(self, company_id: str, event: dict[str, Any]) -> None:
        client = self._get_client()
        if not client:
            return
        channel = f"pixops:events:{company_id}"
        try:
            client.publish(channel, json.dumps(event, ensure_ascii=False))
        except RedisError:
            return


event_bus = EventBus()
