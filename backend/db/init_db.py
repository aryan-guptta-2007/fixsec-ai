"""
Database initialization script for FixSec AI
Handles database creation and migration for production deployments
"""
import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, text
from alembic.config import Config
from alembic import command
import logging

# Add the parent directory to the path
sys.path.append(str(Path(__file__).parent.parent))

from db.session import DATABASE_URL, engine
from db.models import Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_database_if_not_exists():
    """Create database if it doesn't exist (PostgreSQL only)"""
    if not DATABASE_URL.startswith("postgresql"):
        logger.info("Using SQLite - database will be created automatically")
        return
    
    # Extract database name from URL
    # postgresql://user:pass@host:port/dbname
    try:
        db_name = DATABASE_URL.split("/")[-1]
        base_url = "/".join(DATABASE_URL.split("/")[:-1])
        
        # Connect to postgres database to create our database
        postgres_url = f"{base_url}/postgres"
        temp_engine = create_engine(postgres_url)
        
        with temp_engine.connect() as conn:
            # Check if database exists
            result = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
                {"db_name": db_name}
            )
            
            if not result.fetchone():
                logger.info(f"Creating database: {db_name}")
                # Create database (must be outside transaction)
                conn.execute(text("COMMIT"))
                conn.execute(text(f"CREATE DATABASE {db_name}"))
                logger.info(f"Database {db_name} created successfully")
            else:
                logger.info(f"Database {db_name} already exists")
        
        temp_engine.dispose()
        
    except Exception as e:
        logger.error(f"Error creating database: {e}")
        raise

def run_migrations():
    """Run Alembic migrations to create/update schema"""
    try:
        logger.info("Running database migrations...")
        
        # Get the directory containing this script
        current_dir = Path(__file__).parent.parent
        alembic_cfg = Config(str(current_dir / "alembic.ini"))
        
        # Run migrations
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations completed successfully")
        
    except Exception as e:
        logger.error(f"Error running migrations: {e}")
        raise

def verify_database():
    """Verify database connection and schema"""
    try:
        logger.info("Verifying database connection...")
        
        with engine.connect() as conn:
            # Test basic connection
            result = conn.execute(text("SELECT 1"))
            assert result.fetchone()[0] == 1
            
            # Check if our tables exist
            if DATABASE_URL.startswith("postgresql"):
                tables_query = """
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                """
            else:
                tables_query = """
                SELECT name FROM sqlite_master 
                WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
                """
            
            result = conn.execute(text(tables_query))
            tables = [row[0] for row in result.fetchall()]
            
            expected_tables = ["users", "repositories", "scans", "vulnerabilities", "pull_requests"]
            missing_tables = [table for table in expected_tables if table not in tables]
            
            if missing_tables:
                raise Exception(f"Missing tables: {missing_tables}")
            
            logger.info(f"Database verification successful. Tables: {tables}")
            
    except Exception as e:
        logger.error(f"Database verification failed: {e}")
        raise

def init_database():
    """Initialize database for production deployment"""
    logger.info("Initializing FixSec AI database...")
    logger.info(f"Database URL: {DATABASE_URL.split('@')[0]}@***")  # Hide credentials
    
    try:
        # Step 1: Create database if needed
        create_database_if_not_exists()
        
        # Step 2: Run migrations
        run_migrations()
        
        # Step 3: Verify everything is working
        verify_database()
        
        logger.info("✅ Database initialization completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        return False

if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)