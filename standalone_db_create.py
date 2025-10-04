"""
Standalone database creation script for MySQL
"""
import os
import sys
from sqlalchemy import create_engine, inspect
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

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

def test_mysql_connection():
    """Test MySQL connection first"""
    try:
        import pymysql
        
        print("🔌 Testing MySQL connection...")
        
        connection = pymysql.connect(
            host="127.0.0.1",
            user="root",
            password="123@Ujjwal",  # Use actual password, not URL encoded
            port=3306
        )
        
        print("✅ MySQL connection successful!")
        
        # Test if we can create database
        cursor = connection.cursor()
        cursor.execute("CREATE DATABASE IF NOT EXISTS expense_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.execute("SHOW DATABASES LIKE 'expense_system'")
        
        if cursor.fetchone():
            print("✅ Database 'expense_system' is ready")
        else:
            print("❌ Failed to create database")
            return False
            
        connection.close()
        return True
        
    except ImportError:
        print("❌ PyMySQL not installed. Run: pip install pymysql")
        return False
    except Exception as e:
        print(f"❌ MySQL connection failed: {str(e)}")
        print("\n💡 Troubleshooting:")
        print("1. Check if MySQL server is running")
        print("2. Verify username and password")
        print("3. Check if MySQL is listening on port 3306")
        print("4. Try connecting with MySQL Workbench or command line")
        return False

def create_database():
    """Create all database tables in MySQL"""
    try:
        # First test connection
        if not test_mysql_connection():
            return False
        
        # MySQL Database Configuration (matches your .env file)
        DB_HOST = "127.0.0.1"
        DB_USER = "root"
        DB_PASSWORD = "123@Ujjwal"
        DB_NAME = "expense_system"  # ✅ Now matches your .env file
        DB_PORT = 3306
        
        # Create MySQL connection URL with proper encoding
        DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD.replace('@', '%40')}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        
        print(f"\n🗄️ Creating tables in database...")
        print(f"📊 Host: {DB_HOST}")
        print(f"👤 User: {DB_USER}")
        print(f"🗄️ Database: {DB_NAME}")
        
        # Create engine
        engine = create_engine(DATABASE_URL, echo=False)  # Set echo=True to see SQL commands
        
        print("🔨 Creating database tables...")
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        # Verify tables were created
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        print(f"\n✅ Successfully created {len(tables)} tables:")
        for table in sorted(tables):
            print(f"   • {table}")
        
        print(f"\n🎉 MySQL database setup completed!")
        print(f"📊 Database: {DB_NAME}")
        print(f"🔗 Connection: {DB_HOST}:{DB_PORT}")
        print("You can now run the application with: python main.py")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating database: {str(e)}")
        print("\n💡 If this keeps failing, try:")
        print("1. Start MySQL service manually")
        print("2. Check MySQL is running on port 3306")
        print("3. Use SQLite temporarily: DATABASE_URL=sqlite:///./expense_system.db")
        return False

if __name__ == "__main__":
    print("🚀 MySQL Database Setup for Expense Management System")
    print("=" * 60)
    
    create_database()