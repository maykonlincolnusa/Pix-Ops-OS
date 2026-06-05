from collections import defaultdict
from datetime import datetime, timezone
from threading import Lock

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute: int = 240):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self._lock = Lock()
        self._counters: dict[tuple[str, str], int] = defaultdict(int)

    async def dispatch(self, request: Request, call_next):
        now = datetime.now(timezone.utc)
        slot = now.strftime("%Y%m%d%H%M")
        ip = request.client.host if request.client else "unknown"
        tenant = request.headers.get("X-Tenant-ID", "public")
        key = (f"{ip}:{tenant}", slot)

        with self._lock:
            self._counters[key] += 1
            count = self._counters[key]
            # Drop old buckets opportunistically.
            stale_keys = [k for k in self._counters.keys() if k[1] != slot]
            for old in stale_keys[:300]:
                self._counters.pop(old, None)

        if count > self.requests_per_minute:
            return JSONResponse(
                {"detail": "Rate limit exceeded."},
                status_code=429,
            )

        return await call_next(request)
