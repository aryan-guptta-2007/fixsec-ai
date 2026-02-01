from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import auth, repos, scan, pr, history, schedule, workspace, billing
from config import settings

# Initialize Sentry for error tracking in production (optional)
try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    
    if settings.SENTRY_DSN:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            integrations=[FastApiIntegration(auto_enabling=True)],
            traces_sample_rate=0.1,
            environment=settings.ENVIRONMENT,
        )
        print("✅ Sentry initialized for error tracking")
except ImportError:
    print("⚠️ Sentry not available - continuing without error tracking")

app = FastAPI(
    title="FixSec AI - Enterprise Security Scanner",
    description="Automated security vulnerability scanning and remediation platform",
    version="1.0.0",
    docs_url="/docs" if not settings.is_production else None,  # Disable docs in production
    redoc_url="/redoc" if not settings.is_production else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

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
    return {
        "message": "FixSec AI - Enterprise Security Scanner",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "status": "operational"
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "version": "1.0.0"
    }