#!/usr/bin/env python3
"""
Production Database Migration Script
This script handles database initialization and migrations for production deployment.
"""

import os
import sys
import logging
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError

# Add the app directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.core.database import Base
from app.models.models import *  # Import all models

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def wait_for_database(max_retries=30, retry_interval=2):
    """Wait for database to be available"""
    import time
    
    for attempt in range(max_retries):
        try:
            engine = create_engine(settings.database_url)
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            logger.info("✅ Database is available")
            return engine
        except OperationalError as e:
            logger.warning(f"⏳ Database not ready (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_interval)
            else:
                logger.error("❌ Database is not available after maximum retries")
                raise

def create_database_schema(engine):
    """Create database schema"""
    try:
        logger.info("🔨 Creating database schema...")
        Base.metadata.create_all(bind=engine)
        
        # Verify tables were created
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        logger.info(f"✅ Created {len(tables)} tables: {', '.join(tables)}")
        
        return True
    except Exception as e:
        logger.error(f"❌ Failed to create database schema: {e}")
        return False

def create_initial_data(engine):
    """Create initial data for production"""
    from sqlalchemy.orm import sessionmaker
    from app.models.models import Company, User, ExpenseCategory
    from app.core.security import get_password_hash
    
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Check if data already exists
        if db.query(Company).first():
            logger.info("ℹ️ Initial data already exists, skipping creation")
            return True
        
        logger.info("📝 Creating initial data...")
        
        # Create default company
        company = Company(
            name="Default Company",
            address="123 Business Street",
            contact_email="admin@company.com",
            phone="+1-555-0123"
        )
        db.add(company)
        db.flush()
        
        # Create admin user
        admin_user = User(
            email="admin@company.com",
            username="admin",
            full_name="System Administrator",
            hashed_password=get_password_hash("admin123"),
            role="admin",
            company_id=company.id,
            is_active=True
        )
        db.add(admin_user)
        
        # Create default expense categories
        categories = [
            "Travel",
            "Meals & Entertainment",
            "Office Supplies",
            "Training & Education",
            "Software & Subscriptions",
            "Transportation",
            "Accommodation",
            "Equipment",
            "Utilities",
            "Other"
        ]
        
        for category_name in categories:
            category = ExpenseCategory(
                name=category_name,
                description=f"Default category for {category_name.lower()} expenses",
                company_id=company.id
            )
            db.add(category)
        
        db.commit()
        logger.info("✅ Initial data created successfully")
        logger.info("🔑 Default admin credentials:")
        logger.info("   Email: admin@company.com")
        logger.info("   Password: admin123")
        logger.warning("⚠️ Please change the default admin password after first login!")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to create initial data: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def main():
    """Main migration function"""
    logger.info("🚀 Starting production database migration...")
    
    try:
        # Wait for database to be available
        engine = wait_for_database()
        
        # Create schema
        if not create_database_schema(engine):
            sys.exit(1)
        
        # Create initial data
        if not create_initial_data(engine):
            sys.exit(1)
        
        logger.info("🎉 Production database migration completed successfully!")
        
    except Exception as e:
        logger.error(f"💥 Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()