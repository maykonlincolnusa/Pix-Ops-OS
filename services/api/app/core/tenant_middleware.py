from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class TenantContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        tenant_id = request.headers.get("X-Tenant-ID") or request.query_params.get("tenant_id")
        request.state.tenant_id = tenant_id
        return await call_next(request)
