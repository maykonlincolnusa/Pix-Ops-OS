import json
from typing import Any

from redis import Redis
from redis.exceptions import RedisError

from app.core.config import get_settings


class EventBus:
    def __init__(self) -> None:
        self._redis_url = get_settings().redis_url
        self._client: Redis | None = None

    def _get_client(self) -> Redis | None:
        if self._client is not None:
            return self._client
        try:
            self._client = Redis.from_url(self._redis_url, decode_responses=True)
            return self._client
        except RedisError:
            self._client = None
            return None

    def publish_tenant_event(self, tenant_id: str, event: dict[str, Any]) -> None:
        client = self._get_client()
        if not client:
            return
        channel = f"pixops:tenant:{tenant_id}:events"
        try:
            payload = json.dumps(event, ensure_ascii=False, default=str)
            client.publish(channel, payload)
            client.xadd(f"pixops:tenant:{tenant_id}:stream", {"event": payload}, maxlen=10000, approximate=True)
        except RedisError:
            return


event_bus = EventBus()
