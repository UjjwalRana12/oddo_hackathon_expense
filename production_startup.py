#!/usr/bin/env python3
"""
Production Startup Script
Handles pre-flight checks and application startup for production deployment.
"""

import os
import sys
import time
import logging
import subprocess
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_environment():
    """Check required environment variables"""
    required_vars = [
        "DATABASE_URL",
        "SECRET_KEY",
        "EMAIL_USER",
        "EMAIL_PASSWORD"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        return False
    
    logger.info("✅ All required environment variables are set")
    return True

def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        import fastapi
        import sqlalchemy
        import uvicorn
        import pytesseract
        logger.info("✅ Core dependencies available")
        return True
    except ImportError as e:
        logger.error(f"❌ Missing dependency: {e}")
        return False

def check_tesseract():
    """Check if Tesseract OCR is available"""
    try:
        import pytesseract
        # Try to get Tesseract version
        version = pytesseract.get_tesseract_version()
        logger.info(f"✅ Tesseract OCR available (version: {version})")
        return True
    except Exception as e:
        logger.warning(f"⚠️ Tesseract OCR not available: {e}")
        logger.warning("OCR features will be disabled")
        return False

def create_directories():
    """Create necessary directories"""
    directories = [
        os.getenv("UPLOAD_DIR", "/tmp/uploads"),
        "logs"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        logger.info(f"📁 Created directory: {directory}")

def run_database_migration():
    """Run database migration if needed"""
    logger.info("🗄️ Running database migration...")
    try:
        result = subprocess.run([
            sys.executable, "migrate_production.py"
        ], capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            logger.info("✅ Database migration completed")
            return True
        else:
            logger.error(f"❌ Database migration failed: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        logger.error("❌ Database migration timed out")
        return False
    except Exception as e:
        logger.error(f"❌ Database migration error: {e}")
        return False

def start_application():
    """Start the FastAPI application"""
    logger.info("🚀 Starting Expense System API...")
    
    # Determine startup command
    use_gunicorn = os.getenv("USE_GUNICORN", "false").lower() == "true"
    port = int(os.getenv("PORT", 8000))
    workers = int(os.getenv("WORKERS", 4))
    
    if use_gunicorn:
        cmd = [
            "gunicorn", 
            "-c", "gunicorn.conf.py",
            "app.main:app"
        ]
    else:
        cmd = [
            "uvicorn",
            "app.main:app",
            "--host", "0.0.0.0",
            "--port", str(port),
            "--workers", str(workers)
        ]
    
    logger.info(f"🌟 Starting with command: {' '.join(cmd)}")
    
    try:
        os.execvp(cmd[0], cmd)
    except Exception as e:
        logger.error(f"❌ Failed to start application: {e}")
        sys.exit(1)

def main():
    """Main startup function"""
    logger.info("🏁 Starting production deployment checks...")
    
    # Run all pre-flight checks
    checks = [
        ("Environment Variables", check_environment),
        ("Dependencies", check_dependencies),
        ("Tesseract OCR", check_tesseract),
    ]
    
    failed_checks = []
    for check_name, check_func in checks:
        logger.info(f"🔍 Checking {check_name}...")
        if not check_func():
            failed_checks.append(check_name)
    
    # Create necessary directories
    create_directories()
    
    # Run database migration
    if not run_database_migration():
        failed_checks.append("Database Migration")
    
    # Check if any critical checks failed
    critical_failures = [f for f in failed_checks if f not in ["Tesseract OCR"]]
    if critical_failures:
        logger.error(f"💥 Critical checks failed: {', '.join(critical_failures)}")
        sys.exit(1)
    
    if failed_checks:
        logger.warning(f"⚠️ Some non-critical checks failed: {', '.join(failed_checks)}")
    
    logger.info("✅ All critical pre-flight checks passed")
    
    # Start the application
    start_application()

if __name__ == "__main__":
    main()