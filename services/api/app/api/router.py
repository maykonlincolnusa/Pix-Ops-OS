from fastapi import APIRouter

from app.api.routes.agentic import router as agentic_router
from app.api.routes.ai import router as ai_router
from app.api.routes.auth import router as auth_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.developer_api import router as developer_router
from app.api.routes.health import router as health_router
from app.api.routes.payments import router as payments_router
from app.api.routes.setup import router as setup_router
from app.api.routes.webhooks import router as webhooks_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(ai_router)
api_router.include_router(setup_router)
api_router.include_router(payments_router)
api_router.include_router(dashboard_router)
api_router.include_router(webhooks_router)
api_router.include_router(developer_router)
api_router.include_router(agentic_router)
