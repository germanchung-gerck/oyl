from typing import Any, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class TenantContextMiddleware(BaseHTTPMiddleware):
    """Extract tenant context from request headers and attach to request state."""

    async def dispatch(self, request: Request, call_next: Callable[..., Any]) -> Response:
        tenant_id = request.headers.get("X-Tenant-ID")
        request.state.tenant_id = tenant_id
        response = await call_next(request)
        return response
