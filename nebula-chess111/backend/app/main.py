"""
Nebula Chess — FastAPI Application Entry Point
"""
from contextlib import asynccontextmanager
import structlog

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.database import engine, Base
from app.redis_client import get_redis, close_redis
from app.api import auth, users, games, leaderboard, tournaments, puzzles
from app.websocket.handlers import router as ws_router

log = structlog.get_logger()

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("nebula_chess.startup", version=settings.APP_VERSION)
    await get_redis()
    yield
    await close_redis()
    await engine.dispose()
    log.info("nebula_chess.shutdown")


app = FastAPI(
    title="Nebula Chess API",
    version=settings.APP_VERSION,
    description="Premium online chess platform — server-authoritative, real-time, scalable.",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ── Middleware ────────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router,        prefix="/api/auth",         tags=["Auth"])
app.include_router(users.router,       prefix="/api/users",        tags=["Users"])
app.include_router(games.router,       prefix="/api/games",        tags=["Games"])
app.include_router(leaderboard.router, prefix="/api/leaderboard",  tags=["Leaderboard"])
app.include_router(tournaments.router, prefix="/api/tournaments",  tags=["Tournaments"])
app.include_router(puzzles.router,     prefix="/api/puzzles",      tags=["Puzzles"])
app.include_router(ws_router)

# ── Prometheus metrics ────────────────────────────────────────────────────────
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


@app.get("/api/health", tags=["Health"])
async def health():
    return {"status": "ok", "version": settings.APP_VERSION}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    log.error("unhandled_exception", path=request.url.path, error=str(exc))
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
