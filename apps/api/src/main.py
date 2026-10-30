"""ResearchOS API — FastAPI application entry point."""

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from src.config import get_settings
from src.modules.identity.router import router as identity_router
from src.modules.companies.router import router as companies_router
from src.modules.financials.router import router as financials_router
from src.modules.documents.router import router as documents_router
from src.modules.concalls.router import router as concalls_router
from src.modules.announcements.router import router as announcements_router
from src.modules.watchlists.router import router as watchlists_router
from src.modules.ai_research.router import router as ai_router
from src.modules.subscriptions.router import router as subscriptions_router
from src.modules.administration.router import router as admin_router
from src.modules.screening.router import router as screening_router
from src.modules.market_data.router import router as market_data_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    yield


app = FastAPI(
    title=settings.app_name,
    description="Indian-equity research platform API",
    version="0.1.0",
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    response: Response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# Health check
@app.get("/health")
async def health():
    return {"status": "healthy", "app": settings.app_name, "data_mode": settings.data_mode}


@app.get("/ready")
async def readiness():
    return {"status": "ready"}


# API v1 routes
PREFIX = "/api/v1"
app.include_router(identity_router, prefix=f"{PREFIX}/auth", tags=["Authentication"])
app.include_router(companies_router, prefix=f"{PREFIX}/companies", tags=["Companies"])
app.include_router(market_data_router, prefix=f"{PREFIX}", tags=["Market Data"])
app.include_router(financials_router, prefix=f"{PREFIX}", tags=["Financials"])
app.include_router(documents_router, prefix=f"{PREFIX}", tags=["Documents"])
app.include_router(concalls_router, prefix=f"{PREFIX}", tags=["Concalls"])
app.include_router(announcements_router, prefix=f"{PREFIX}", tags=["Announcements"])
app.include_router(watchlists_router, prefix=f"{PREFIX}/watchlists", tags=["Watchlists"])
app.include_router(screening_router, prefix=f"{PREFIX}/screener", tags=["Screener"])
app.include_router(ai_router, prefix=f"{PREFIX}/ai", tags=["AI Research"])
app.include_router(subscriptions_router, prefix=f"{PREFIX}/subscription", tags=["Subscriptions"])
app.include_router(admin_router, prefix=f"{PREFIX}/admin", tags=["Administration"])
