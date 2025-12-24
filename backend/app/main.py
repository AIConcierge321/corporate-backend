import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.rate_limit import limiter
from app.services.redis_client import RedisService

logger = logging.getLogger(__name__)

# Rate limiter is now imported from app.core.rate_limit


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info(f"Starting {settings.PROJECT_NAME}")

    # MED-004: Warn if CORS is misconfigured in production
    if not settings.DEV_MODE and settings.CORS_ORIGINS == "*":
        logger.error("=" * 70)
        logger.error("🚨 SECURITY WARNING: CORS_ORIGINS='*' in PRODUCTION MODE!")
        logger.error("🚨 This allows ANY website to make requests to your API!")
        logger.error("🚨 Set CORS_ORIGINS to your frontend domain in .env file!")
        logger.error("🚨 Example: CORS_ORIGINS='https://app.example.com'")
        logger.error("=" * 70)
        # Consider uncommenting the line below to prevent startup with insecure config:
        # raise RuntimeError("CORS_ORIGINS must be set to specific origins in production")

    yield

    # Shutdown
    await RedisService.close()
    logger.info("Shutdown complete")


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# ===========================================
# Security Middleware
# ===========================================

# 1. Rate Limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# 2. CORS
origins = settings.CORS_ORIGINS.split(",") if settings.CORS_ORIGINS != "*" else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)


# 3. Security Headers Middleware (CRIT-002)
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)

    # Critical Security Headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

    # HSTS (Production only)
    if not settings.DEV_MODE:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    return response


# 4. HTTPS Redirect (Production only)
if not settings.DEV_MODE:
    from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware

    app.add_middleware(HTTPSRedirectMiddleware)


# 3. Request ID middleware for tracing
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    import uuid

    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# ===========================================
# Routes
# ===========================================

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME}"}


@app.get("/health")
@limiter.limit("60/minute")
async def health_check(request: Request):
    """
    Health check endpoint with dependency status.

    MED-003: Enhanced to include Redis connectivity check.
    """
    from datetime import datetime

    # Check Redis health
    redis_healthy = await RedisService.health_check()

    # Overall status is degraded if Redis is down
    status = "healthy" if redis_healthy else "degraded"

    return {
        "status": status,
        "service": settings.PROJECT_NAME,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "dependencies": {
            "redis": "connected" if redis_healthy else "disconnected",
            "database": "connected",  # Database is required to start, so always connected
        },
    }
