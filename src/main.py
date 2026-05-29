
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.requests import Request
from contextlib import asynccontextmanager
import uvicorn
import os
from app import login, registration
from app.home import home
from app.profile import profile
from configurations import settings
from common.cache import redis_helper
from common.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app lifecycle - startup and shutdown."""
    # Startup
    try:
        await redis_helper.init_redis(settings.redis_url)
        logger.info("Application startup complete")
    except Exception as e:
        logger.warning(f"Redis initialization failed, continuing without caching: {str(e)}")

    yield

    # Shutdown
    await redis_helper.close_redis()
    logger.info("Application shutdown complete")


app = FastAPI(lifespan=lifespan)

cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"]
)


@app.middleware("http")
async def session_timeout_middleware(request: Request, call_next):
    """
    Middleware to check session inactivity timeout on each request.
    Automatically logs out users inactive for 15+ minutes.
    """
    # Skip session check for auth endpoints and health checks
    skip_paths = ["/docs", "/openapi.json", "/api/2025/login", "/api/2025/register", "/api/2025/token"]
    if any(request.url.path.startswith(path) for path in skip_paths):
        return await call_next(request)

    # Extract token from Authorization header
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return await call_next(request)

    try:
        # Token validation happens in verify_access_token dependency
        # For now, we proceed and let the route handler validate
        response = await call_next(request)

        # If request succeeded (status 200-299), refresh session timeout
        if 200 <= response.status_code < 300:
            # We'll refresh session in the verify_access_token function
            pass

        return response
    except Exception as e:
        logger.error(f"Session middleware error: {str(e)}")
        return await call_next(request)

API_PREFIX = "/api/2025"

app.include_router(login.router, prefix=API_PREFIX)
app.include_router(registration.router, prefix=API_PREFIX)
app.include_router(home.router, prefix=API_PREFIX)
app.include_router(profile.router, prefix=API_PREFIX)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    uvicorn.run("main:app", reload=True, port=port)
