from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import os
import logging
import time
from sqlalchemy import inspect

from .core.database import engine, Base
from .api import auth, users, expenses, approvals, approval_rules, currency, categories
from .core.config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def ensure_database_exists():
    """Ensure database tables exist, create them if they don't"""
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if not tables:
            logger.info("📋 No tables found, creating database schema...")
            Base.metadata.create_all(bind=engine)
            
            # Verify tables were created
            tables = inspector.get_table_names()
            logger.info(f"✅ Created {len(tables)} tables: {', '.join(tables)}")
        else:
            logger.info(f"✅ Database ready with {len(tables)} tables")
            
    except Exception as e:
        logger.error(f"❌ Database initialization error: {str(e)}")
        if settings.environment == "production":
            raise
        else:
            logger.warning("⚠️ Continuing in development mode without database")

# Initialize database
ensure_database_exists()

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="A comprehensive expense reimbursement system with OCR support and flexible approval workflows",
    version="1.0.0",
    debug=settings.debug,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# Security middleware - Trust only allowed hosts
if settings.environment == "production":
    app.add_middleware(
        TrustedHostMiddleware, 
        allowed_hosts=settings.allowed_hosts
    )

# CORS middleware with production-safe configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)

# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Security headers middleware
@app.middleware("http") 
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if settings.environment == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# Custom exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"Validation error on {request.url}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Invalid request data", "errors": exc.errors()}
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning(f"HTTP error on {request.url}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unexpected error on {request.url}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )

# Create upload directory if it doesn't exist
os.makedirs(settings.upload_dir, exist_ok=True)

# Mount static files (only in development or with proper security)
if settings.debug or settings.environment != "production":
    app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(expenses.router, prefix="/api/expenses", tags=["Expenses"])
app.include_router(approvals.router, prefix="/api/approvals", tags=["Approvals"])
app.include_router(approval_rules.router, prefix="/api/approval-rules", tags=["Approval Rules"])
app.include_router(currency.router, prefix="/api/currency", tags=["Currency"])
app.include_router(categories.router, prefix="/api/categories", tags=["Categories"])

@app.get("/")
async def root():
    """
    Root endpoint
    """
    return {
        "message": "Welcome to the Expense Reimbursement System API",
        "version": "1.0.0",
        "environment": settings.environment,
        "docs": "/docs" if settings.debug else "Not available in production"
    }

@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring
    """
    try:
        # Test database connection
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Health check database error: {e}")
        db_status = "unhealthy"
    
    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "database": db_status,
        "environment": settings.environment,
        "timestamp": time.time()
    }

@app.on_event("startup")
async def startup_event():
    """
    Startup event handler
    """
    logger.info("🚀 Expense Reimbursement System API starting up...")
    logger.info(f"📊 Environment: {settings.environment}")
    logger.info(f"🗄️ Database: {'PostgreSQL' if 'postgresql' in settings.database_url else 'SQLite'}")
    logger.info(f"📁 Upload directory: {settings.upload_dir}")
    if settings.debug:
        logger.info("🌐 Access the API at:")
        logger.info("   • Main API: http://localhost:8000")
        logger.info("   • API Docs: http://localhost:8000/docs")
        logger.info("   • ReDoc: http://localhost:8000/redoc")

@app.on_event("shutdown")
async def shutdown_event():
    """
    Shutdown event handler
    """
    logger.info("🛑 Expense Reimbursement System API shutting down...")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",  # Changed for production compatibility
        port=int(os.getenv("PORT", 8000)),  # Use PORT env var for deployment platforms
        reload=settings.debug,
        workers=1 if settings.debug else settings.workers,
        access_log=settings.debug
    )