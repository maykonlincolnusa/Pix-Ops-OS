from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from app.api.router import api_router
from app.core.config import get_settings
from app.core.rate_limit_middleware import RateLimitMiddleware
from app.core.tenant_middleware import TenantContextMiddleware
from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.session import engine

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.2.0",
    description="PixOps OS API: Real-Time Payment Operations, Reconciliation & Anti-Fraud Platform.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TenantContextMiddleware)
app.add_middleware(RateLimitMiddleware, requests_per_minute=300)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/")
def root() -> dict:
    return {
        "name": settings.app_name,
        "version": "0.2.0",
        "docs": "/docs",
        "product": "PixOps OS",
    }


app.include_router(api_router)
FastAPIInstrumentor.instrument_app(app)
