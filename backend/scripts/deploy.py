#!/usr/bin/env python3
"""
Production deployment script for FixSec AI
Handles database migrations and application startup
"""
import os
import sys
import subprocess
import logging
from pathlib import Path

# Add the parent directory to the path
sys.path.append(str(Path(__file__).parent.parent))

from db.init_db import init_database

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_environment():
    """Check that required environment variables are set"""
    required_vars = [
        "GITHUB_CLIENT_ID",
        "GITHUB_CLIENT_SECRET", 
        "SECRET_KEY"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        return False
    
    logger.info("✅ Environment variables check passed")
    return True

def install_dependencies():
    """Install Python dependencies"""
    try:
        logger.info("Installing Python dependencies...")
        
        # Use production requirements if available
        requirements_file = "requirements-prod.txt" if os.path.exists("requirements-prod.txt") else "requirements.txt"
        
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", requirements_file
        ], check=True, capture_output=True)
        
        logger.info("✅ Dependencies installed successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Failed to install dependencies: {e}")
        return False

def run_database_migrations():
    """Run database migrations"""
    try:
        logger.info("Running database migrations...")
        
        success = init_database()
        if success:
            logger.info("✅ Database migrations completed")
            return True
        else:
            logger.error("❌ Database migrations failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Database migration error: {e}")
        return False

def start_application():
    """Start the FastAPI application"""
    try:
        logger.info("Starting FixSec AI application...")
        
        # Get configuration from environment
        host = os.getenv("API_HOST", "0.0.0.0")
        port = int(os.getenv("API_PORT", "8000"))
        workers = int(os.getenv("WORKERS", "1"))
        
        # Start with uvicorn
        cmd = [
            "uvicorn", "main:app",
            "--host", host,
            "--port", str(port),
            "--workers", str(workers)
        ]
        
        # Add production settings
        if os.getenv("ENVIRONMENT") == "production":
            cmd.extend(["--access-log", "--no-use-colors"])
        else:
            cmd.append("--reload")
        
        logger.info(f"Starting server: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
        
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Application failed to start: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return False

def deploy():
    """Main deployment function"""
    logger.info("🚀 Starting FixSec AI deployment...")
    
    # Change to backend directory
    backend_dir = Path(__file__).parent.parent
    os.chdir(backend_dir)
    logger.info(f"Working directory: {backend_dir}")
    
    # Step 1: Check environment
    if not check_environment():
        logger.error("❌ Environment check failed")
        return False
    
    # Step 2: Install dependencies
    if not install_dependencies():
        logger.error("❌ Dependency installation failed")
        return False
    
    # Step 3: Run database migrations
    if not run_database_migrations():
        logger.error("❌ Database migration failed")
        return False
    
    # Step 4: Start application
    logger.info("✅ Deployment preparation complete")
    start_application()
    
    return True

if __name__ == "__main__":
    success = deploy()
    sys.exit(0 if success else 1)