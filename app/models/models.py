from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from datetime import datetime

Base = declarative_base()

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

class Company(Base):
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    country = Column(String(100), nullable=False)
    currency = Column(String(3), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    users = relationship("User", back_populates="company")
    expenses = relationship("Expense", back_populates="company")
    approval_rules = relationship("ApprovalRule", back_populates="company")
    categories = relationship("Category", back_populates="company")

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
    
    # Relationships - Fixed the overlap issue
    company = relationship("Company", back_populates="users")
    manager = relationship("User", remote_side=[id], back_populates="employees")
    employees = relationship("User", back_populates="manager", overlaps="manager")  # Fixed overlap
    
    # Expense relationships
    submitted_expenses = relationship("Expense", foreign_keys="Expense.employee_id", back_populates="employee")
    approvals = relationship("Approval", back_populates="approver")

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

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
    
    # Foreign Keys
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    employee = relationship("User", foreign_keys=[employee_id], back_populates="submitted_expenses")
    company = relationship("Company", back_populates="expenses")
    approvals = relationship("Approval", back_populates="expense")

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
    
    # Relationships
    expense = relationship("Expense", back_populates="approvals")
    approver = relationship("User", back_populates="approvals")

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
    
    # Relationships
    company = relationship("Company", back_populates="approval_rules")
    specific_approver = relationship("User", foreign_keys=[specific_approver_id])
    rule_approvers = relationship("ApprovalRuleApprover", back_populates="rule")

class ApprovalRuleApprover(Base):
    __tablename__ = "approval_rule_approvers"
    
    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(Integer, ForeignKey("approval_rules.id"), nullable=False)
    approver_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    sequence = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    rule = relationship("ApprovalRule", back_populates="rule_approvers")
    approver = relationship("User")

class Category(Base):
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    company = relationship("Company", back_populates="categories")