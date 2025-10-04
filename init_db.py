from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine
from app.models.models import Base, User, Company, ExpenseCategory
from app.core.security import get_password_hash
import asyncio

def create_default_data():
    """Create default data for testing"""
    db = SessionLocal()
    
    try:
        # Create default company
        company = Company(
            name="Demo Company",
            country="United States",
            currency="USD"
        )
        db.add(company)
        db.flush()
        
        # Create default admin user
        admin_user = User(
            email="admin@democompany.com",
            hashed_password=get_password_hash("admin123"),
            first_name="Admin",
            last_name="User",
            role="admin",
            company_id=company.id,
            is_active=True
        )
        db.add(admin_user)
        
        # Create default manager
        manager_user = User(
            email="manager@democompany.com",
            hashed_password=get_password_hash("manager123"),
            first_name="Manager",
            last_name="User",
            role="manager",
            company_id=company.id,
            is_active=True
        )
        db.add(manager_user)
        
        # Create default employee
        employee_user = User(
            email="employee@democompany.com",
            hashed_password=get_password_hash("employee123"),
            first_name="Employee",
            last_name="User",
            role="employee",
            company_id=company.id,
            manager_id=manager_user.id,
            is_active=True
        )
        db.add(employee_user)
        
        # Create default expense categories
        categories = [
            {"name": "Food & Dining", "description": "Restaurant meals and food expenses"},
            {"name": "Transportation", "description": "Travel, taxi, and transportation costs"},
            {"name": "Accommodation", "description": "Hotel and lodging expenses"},
            {"name": "Office Supplies", "description": "Office equipment and supplies"},
            {"name": "Training & Education", "description": "Training courses and educational materials"},
            {"name": "Other", "description": "Miscellaneous expenses"}
        ]
        
        for cat_data in categories:
            category = ExpenseCategory(
                name=cat_data["name"],
                description=cat_data["description"],
                company_id=company.id,
                is_active=True
            )
            db.add(category)
        
        db.commit()
        print("✅ Default data created successfully!")
        print("📧 Admin user: admin@democompany.com / admin123")
        print("📧 Manager user: manager@democompany.com / manager123")
        print("📧 Employee user: employee@democompany.com / employee123")
        
    except Exception as e:
        print(f"❌ Error creating default data: {e}")
        db.rollback()
    finally:
        db.close()

def init_db():
    """Initialize database"""
    print("🔄 Initializing database...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created!")
    
    # Check if we need to create default data
    db = SessionLocal()
    try:
        user_count = db.query(User).count()
        if user_count == 0:
            print("🔄 Creating default data...")
            create_default_data()
    finally:
        db.close()

if __name__ == "__main__":
    init_db()