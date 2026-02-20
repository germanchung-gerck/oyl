from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.v1.router import router as api_v1_router
from app.middleware.tenant_context import TenantContextMiddleware

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TenantContextMiddleware)

app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok", "version": settings.APP_VERSION}
