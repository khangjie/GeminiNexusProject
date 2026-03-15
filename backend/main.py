from contextlib import asynccontextmanager
import logging
import os
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import init_db
from app.core.rate_limit import RateLimitMiddleware
from app.api.routes import auth, companies, receipts, approvals, settings as settings_router, workers, analytics

settings = get_settings()
logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    level_name = (settings.LOG_LEVEL or "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    # Keep output in stdout/stderr so Cloud Run ingests it into Cloud Logging.
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        force=True,
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Ensure agent namespaces follow configured level even under server logging config.
    logging.getLogger("agents").setLevel(level)
    logging.getLogger("app").setLevel(level)


_configure_logging()
logger.info("Logging configured with LOG_LEVEL=%s", settings.LOG_LEVEL)

if settings.GOOGLE_APPLICATION_CREDENTIALS:
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = settings.GOOGLE_APPLICATION_CREDENTIALS


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialise database tables
    init_db()
    yield
    # Shutdown: nothing to clean up currently


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="AI-powered expense management backend with multi-agent ADK orchestration.",
    lifespan=lifespan,
)

app.add_middleware(RateLimitMiddleware)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    started = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - started) * 1000
    logger.info(
        "HTTP %s %s -> %s in %.1fms",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response

# CORS — allow the React frontend to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(companies.router, prefix="/api/v1")
app.include_router(receipts.router, prefix="/api/v1")
app.include_router(approvals.router, prefix="/api/v1")
app.include_router(settings_router.router, prefix="/api/v1")
app.include_router(workers.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")


@app.get("/health")
def health_check():
    return {"status": "ok", "app": settings.APP_NAME}
