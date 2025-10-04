from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from sqlalchemy import inspect

from .core.database import engine, Base
from .api import auth, users, expenses, approvals, approval_rules, currency, categories
from .core.config import settings

def ensure_database_exists():
    """Ensure database tables exist, create them if they don't"""
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if not tables:
            print("📋 No tables found, creating database schema...")
            Base.metadata.create_all(bind=engine)
            
            # Verify tables were created
            tables = inspector.get_table_names()
            print(f"✅ Created {len(tables)} tables: {', '.join(tables)}")
        else:
            print(f"✅ Database ready with {len(tables)} tables")
            
    except Exception as e:
        print(f"❌ Database initialization error: {str(e)}")
        raise

# Ensure database exists before creating app
ensure_database_exists()

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="A comprehensive expense reimbursement system with OCR support and flexible approval workflows",
    version="1.0.0",
    debug=settings.debug
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create upload directory if it doesn't exist
os.makedirs(settings.upload_dir, exist_ok=True)

# Mount static files
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
        "docs": "/docs",
        "redoc": "/redoc"
    }

@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {"status": "healthy", "message": "API is running"}

@app.on_event("startup")
async def startup_event():
    """
    Startup event handler
    """
    print("🚀 Expense Reimbursement System API starting up...")
    print(f"📊 Debug mode: {settings.debug}")
    print(f"🗄️ Database: {settings.database_url}")
    print(f"📁 Upload directory: {settings.upload_dir}")
    print("🌐 Access the API at:")
    print("   • Main API: http://localhost:8000")
    print("   • API Docs: http://localhost:8000/docs")
    print("   • ReDoc: http://localhost:8000/redoc")

@app.on_event("shutdown")
async def shutdown_event():
    """
    Shutdown event handler
    """
    print("🛑 Expense Reimbursement System API shutting down...")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",  
        port=8000,
        reload=settings.debug
    )