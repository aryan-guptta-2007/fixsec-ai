"""
Production configuration for FixSec AI
"""
import os
from typing import Optional

class Settings:
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # API Configuration
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    
    # Database
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")
    
    # Redis (for caching and background tasks)
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL")
    
    # GitHub OAuth
    GITHUB_CLIENT_ID: str = os.getenv("GITHUB_CLIENT_ID", "")
    GITHUB_CLIENT_SECRET: str = os.getenv("GITHUB_CLIENT_SECRET", "")
    GITHUB_REDIRECT_URI: str = os.getenv("GITHUB_REDIRECT_URI", "")
    
    # Frontend URL
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    
    # CORS Origins
    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001").split(",")
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    
    # Monitoring
    SENTRY_DSN: Optional[str] = os.getenv("SENTRY_DSN")
    
    # Email (for notifications)
    SENDGRID_API_KEY: Optional[str] = os.getenv("SENDGRID_API_KEY")
    FROM_EMAIL: str = os.getenv("FROM_EMAIL", "noreply@fixsec.ai")
    
    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    
    # Stripe Configuration
    STRIPE_PUBLISHABLE_KEY: str = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    STRIPE_PRO_PRICE_ID: str = os.getenv("STRIPE_PRO_PRICE_ID", "")
    STRIPE_TEAM_PRICE_ID: str = os.getenv("STRIPE_TEAM_PRICE_ID", "")
    
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"
    
    @property
    def database_url_sync(self) -> str:
        """Convert async database URL to sync for SQLAlchemy"""
        if self.DATABASE_URL and self.DATABASE_URL.startswith("postgresql://"):
            return self.DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)
        return self.DATABASE_URL or "sqlite:///./fixsec.db"

settings = Settings()