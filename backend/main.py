import sys

# Windows consoles and pipes default to a legacy code page that cannot encode
# the emoji used in log output, which would otherwise crash whatever printed it.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from core.billing import BillingManager  # noqa: F401  (validates plan config at import)
from core.github import GitHubError
from core.scan_engine import PlanLimitError
from core.scheduler import SchedulerThread
from core.workspace import WorkspaceError
from routes import auth, billing, history, pr, repos, scan, schedule, workspace

logging.basicConfig(level=logging.DEBUG if settings.DEBUG else logging.INFO)
logger = logging.getLogger(__name__)

settings.validate()

if settings.SENTRY_DSN:
    try:
        import sentry_sdk

        # The FastAPI integration turns itself on when the package is present.
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            traces_sample_rate=0.1,
            environment=settings.ENVIRONMENT,
        )
    except ImportError:
        logger.warning("SENTRY_DSN is set but sentry-sdk is not installed")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    scheduler = SchedulerThread()
    if settings.SCHEDULER_ENABLED:
        scheduler.start()
    yield
    if settings.SCHEDULER_ENABLED:
        scheduler.stop()


app = FastAPI(
    title="FixSec AI - Security Scanner",
    description="Automated security vulnerability scanning and remediation platform",
    version="1.0.0",
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.exception_handler(GitHubError)
def handle_github_error(_request: Request, exc: GitHubError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.exception_handler(WorkspaceError)
def handle_workspace_error(_request: Request, exc: WorkspaceError):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(PlanLimitError)
def handle_plan_limit(_request: Request, exc: PlanLimitError):
    return JSONResponse(status_code=402, content={"detail": exc.detail})


app.include_router(auth.router, prefix="/auth")
app.include_router(repos.router, prefix="/repos")
app.include_router(scan.router, prefix="/scan")
app.include_router(pr.router, prefix="/pr")
app.include_router(history.router, prefix="/history")
app.include_router(schedule.router, prefix="/schedule")
app.include_router(workspace.router, prefix="/workspace")
app.include_router(billing.router, prefix="/billing")


@app.get("/")
def root():
    return {"message": "FixSec AI", "version": "1.0.0", "status": "operational"}


@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "1.0.0"}
