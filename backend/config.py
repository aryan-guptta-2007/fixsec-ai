"""
Application configuration for FixSec AI.

Everything is read from the environment (or backend/.env in development).
"""
import os
from typing import List, Optional

from dotenv import load_dotenv

load_dotenv()

DEFAULT_SECRET_KEY = "your-secret-key-change-in-production"


def _split_csv(value: str) -> List[str]:
    return [item.strip().rstrip("/") for item in value.split(",") if item.strip()]


class Settings:
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

    # Database
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")

    # GitHub OAuth
    GITHUB_CLIENT_ID: str = os.getenv("GITHUB_CLIENT_ID", "")
    GITHUB_CLIENT_SECRET: str = os.getenv("GITHUB_CLIENT_SECRET", "")
    GITHUB_REDIRECT_URI: str = os.getenv("GITHUB_REDIRECT_URI", "")

    # GitHub endpoints (override for GitHub Enterprise)
    GITHUB_API_URL: str = os.getenv("GITHUB_API_URL", "https://api.github.com").rstrip("/")
    GITHUB_WEB_URL: str = os.getenv("GITHUB_WEB_URL", "https://github.com").rstrip("/")

    # Public URLs
    BACKEND_URL: str = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")

    # CORS Origins
    CORS_ORIGINS: List[str] = _split_csv(
        os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001")
    )

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", DEFAULT_SECRET_KEY)
    SESSION_TTL_HOURS: int = int(os.getenv("SESSION_TTL_HOURS", "168"))

    # Monitoring
    SENTRY_DSN: Optional[str] = os.getenv("SENTRY_DSN")

    # Email (for notifications)
    SENDGRID_API_KEY: Optional[str] = os.getenv("SENDGRID_API_KEY")
    FROM_EMAIL: str = os.getenv("FROM_EMAIL", "noreply@fixsec.ai")

    # Stripe Configuration
    STRIPE_PUBLISHABLE_KEY: str = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    STRIPE_STARTER_PRICE_ID: str = os.getenv("STRIPE_STARTER_PRICE_ID", "")
    STRIPE_PRO_PRICE_ID: str = os.getenv("STRIPE_PRO_PRICE_ID", "")
    STRIPE_TEAM_PRICE_ID: str = os.getenv("STRIPE_TEAM_PRICE_ID", "")

    # Background scheduler
    SCHEDULER_ENABLED: bool = os.getenv("SCHEDULER_ENABLED", "true").lower() == "true"
    SCHEDULER_INTERVAL_SECONDS: int = int(os.getenv("SCHEDULER_INTERVAL_SECONDS", "60"))

    # Where repositories are cloned while they are being processed
    WORKSPACE_DIR: str = os.getenv("WORKSPACE_DIR", "workspace")

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def github_redirect_uri(self) -> str:
        return self.GITHUB_REDIRECT_URI or f"{self.BACKEND_URL}/auth/github/callback"

    @property
    def allowed_origins(self) -> List[str]:
        return sorted(set(self.CORS_ORIGINS) | {self.FRONTEND_URL})

    @property
    def database_url(self) -> str:
        """Database URL with hosting-provider quirks normalised for SQLAlchemy."""
        url = self.DATABASE_URL or "sqlite:///./fixsec.db"
        if url.startswith("postgres://"):  # Railway/Heroku style
            url = url.replace("postgres://", "postgresql://", 1)
        return url

    def validate(self) -> None:
        """Refuse to boot production with a key that is public in the repository."""
        if self.is_production and (
            self.SECRET_KEY == DEFAULT_SECRET_KEY or len(self.SECRET_KEY) < 32
        ):
            raise RuntimeError(
                "SECRET_KEY must be set to a private random value of at least 32 "
                "characters in production."
            )


settings = Settings()
