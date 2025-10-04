"""
Universal database creation script (SQLite/PostgreSQL/MySQL)
"""
import os
from sqlalchemy import create_engine, inspect
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import enum

# Use environment variable or fallback
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./expense_system.db")

# Create base
Base = declarative_base()

# Define enums
class UserRole(str, enum.Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    EMPLOYEE = "employee"

class ExpenseStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class ExpenseCategory(str, enum.Enum):
    FOOD_DINING = "food_dining"
    TRANSPORTATION = "transportation"
    ACCOMMODATION = "accommodation"
    OFFICE_SUPPLIES = "office_supplies"
    TRAVEL = "travel"
    ENTERTAINMENT = "entertainment"
    OTHER = "other"

class ApprovalRuleType(str, enum.Enum):
    PERCENTAGE = "percentage"
    SPECIFIC_APPROVER = "specific_approver"
    HYBRID = "hybrid"

# Define models
class Company(Base):
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    country = Column(String(100), nullable=False)
    currency = Column(String(3), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.EMPLOYEE)
    is_active = Column(Boolean, default=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    manager_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Expense(Base):
    __tablename__ = "expenses"
    
    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False)
    category = Column(SQLEnum(ExpenseCategory), nullable=False)
    description = Column(Text, nullable=False)
    expense_date = Column(DateTime, nullable=False)
    receipt_url = Column(String(500), nullable=True)
    status = Column(SQLEnum(ExpenseStatus), default=ExpenseStatus.PENDING)
    amount_in_company_currency = Column(Float, nullable=False)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Approval(Base):
    __tablename__ = "approvals"
    
    id = Column(Integer, primary_key=True, index=True)
    expense_id = Column(Integer, ForeignKey("expenses.id"), nullable=False)
    approver_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(SQLEnum(ExpenseStatus), default=ExpenseStatus.PENDING)
    sequence = Column(Integer, default=1)
    comments = Column(Text, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class ApprovalRule(Base):
    __tablename__ = "approval_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    rule_type = Column(SQLEnum(ApprovalRuleType), nullable=False)
    min_amount = Column(Float, nullable=True)
    max_amount = Column(Float, nullable=True)
    percentage_required = Column(Float, nullable=True)
    specific_approver_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class ApprovalRuleApprover(Base):
    __tablename__ = "approval_rule_approvers"
    
    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(Integer, ForeignKey("approval_rules.id"), nullable=False)
    approver_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    sequence = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Category(Base):
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

def get_engine():
    """Create appropriate engine based on DATABASE_URL"""
    if DATABASE_URL.startswith("postgresql"):
        # PostgreSQL (Render)
        engine = create_engine(DATABASE_URL, echo=False)
        print("🐘 Using PostgreSQL database")
    elif DATABASE_URL.startswith("mysql"):
        # MySQL
        engine = create_engine(DATABASE_URL, echo=False)
        print("🐬 Using MySQL database")
    else:
        # SQLite (local development)
        engine = create_engine(DATABASE_URL, echo=False)
        print("📁 Using SQLite database")
    
    return engine

def create_database():
    """Create all database tables"""
    try:
        print(f"🔌 Connecting to database...")
        print(f"📊 URL: {DATABASE_URL[:50]}...")  # Don't show full URL for security
        
        engine = get_engine()
        
        print("🔨 Creating database tables...")
        Base.metadata.create_all(bind=engine)
        
        # Verify tables
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        print(f"\n✅ Successfully created {len(tables)} tables:")
        for table in sorted(tables):
            print(f"   • {table}")
        
        print(f"\n🎉 Database setup completed!")
        return True
        
    except Exception as e:
        print(f"❌ Error creating database: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Universal Database Setup")
    print("=" * 50)
    create_database()