from pydantic_settings import BaseSettings
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    EMPLOYEE = "employee"

class ExpenseStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class ExpenseCategory(str, Enum):
    FOOD_DINING = "food_dining"
    TRANSPORTATION = "transportation"
    ACCOMMODATION = "accommodation"
    OFFICE_SUPPLIES = "office_supplies"
    TRAVEL = "travel"
    ENTERTAINMENT = "entertainment"
    OTHER = "other"

class ApprovalRuleType(str, Enum):
    PERCENTAGE = "percentage"
    SPECIFIC_APPROVER = "specific_approver"
    HYBRID = "hybrid"

# Base schemas with ConfigDict for Pydantic V2
class UserBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    email: EmailStr
    full_name: str
    role: UserRole = UserRole.EMPLOYEE
    is_active: bool = True

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)
    company_name: Optional[str] = None
    country: Optional[str] = None

class UserUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    manager_id: Optional[int] = None

class User(UserBase):
    id: int
    company_id: int
    manager_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: User

# Additional auth schemas that were missing
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class SignupRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str  # Changed from first_name/last_name to full_name
    company_name: str
    country: str

# Company schemas
class CompanyBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    name: str
    country: str
    currency: str

class CompanyCreate(CompanyBase):
    pass

class Company(CompanyBase):
    id: int
    created_at: datetime
    updated_at: datetime

# Expense schemas
class ExpenseBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    amount: float = Field(..., gt=0)
    currency: str = Field(..., max_length=3)
    category: ExpenseCategory
    description: str
    expense_date: datetime
    receipt_url: Optional[str] = None

class ExpenseCreate(ExpenseBase):
    pass

class ExpenseUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    amount: Optional[float] = Field(None, gt=0)
    currency: Optional[str] = Field(None, max_length=3)
    category: Optional[ExpenseCategory] = None
    description: Optional[str] = None
    expense_date: Optional[datetime] = None
    receipt_url: Optional[str] = None

class Expense(ExpenseBase):
    id: int
    employee_id: int
    company_id: int
    status: ExpenseStatus
    amount_in_company_currency: float
    created_at: datetime
    updated_at: datetime

# Approval schemas
class ApprovalBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    comments: Optional[str] = None

class ApprovalCreate(ApprovalBase):
    expense_id: int
    approver_id: int
    sequence: int = 1

class ApprovalAction(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    action: str = Field(..., pattern="^(approve|reject)$")  # Fixed: changed from regex to pattern
    comments: Optional[str] = None

class Approval(ApprovalBase):
    id: int
    expense_id: int
    approver_id: int
    status: ExpenseStatus
    sequence: int
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

# Approval Rule schemas
class ApprovalRuleBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    name: str
    rule_type: ApprovalRuleType
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    percentage_required: Optional[float] = Field(None, ge=0, le=100)
    specific_approver_id: Optional[int] = None
    is_active: bool = True

class ApprovalRuleCreate(ApprovalRuleBase):
    approver_ids: List[int] = []

class ApprovalRuleUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    name: Optional[str] = None
    rule_type: Optional[ApprovalRuleType] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    percentage_required: Optional[float] = Field(None, ge=0, le=100)
    specific_approver_id: Optional[int] = None
    is_active: Optional[bool] = None
    approver_ids: Optional[List[int]] = None

class ApprovalRule(ApprovalRuleBase):
    id: int
    company_id: int
    created_at: datetime
    updated_at: datetime

# Category schemas
class CategoryBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    name: str
    description: Optional[str] = None
    is_active: bool = True

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class Category(CategoryBase):
    id: int
    company_id: int
    created_at: datetime
    updated_at: datetime

# Add missing ExpenseCategory schemas that are being imported
class ExpenseCategoryCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    name: str
    description: Optional[str] = None
    is_active: bool = True

class ExpenseCategoryUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class ExpenseCategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    description: Optional[str] = None
    is_active: bool
    company_id: int
    created_at: datetime
    updated_at: datetime

# OCR schemas
class OCRResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    amount: Optional[float] = None
    currency: Optional[str] = None
    date: Optional[str] = None
    merchant: Optional[str] = None
    description: Optional[str] = None
    category: Optional[ExpenseCategory] = None
    confidence: float = Field(..., ge=0, le=1)
    raw_text: str

class ExpenseFromOCR(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    amount: float = Field(..., gt=0)
    currency: str = Field(default="USD", max_length=3)
    category: ExpenseCategory = ExpenseCategory.OTHER
    description: str
    expense_date: datetime
    receipt_url: str

# Currency schemas
class CurrencyConversion(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    from_currency: str = Field(..., max_length=3)
    to_currency: str = Field(..., max_length=3)
    amount: float = Field(..., gt=0)

class CurrencyConversionResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    from_currency: str
    to_currency: str
    original_amount: float
    converted_amount: float
    exchange_rate: float
    conversion_date: datetime

class Country(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    name: str
    currencies: dict

# Statistics schemas
class ExpenseStats(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    total_expenses: int
    total_amount: float
    pending_count: int
    approved_count: int
    rejected_count: int
    pending_amount: float
    approved_amount: float
    rejected_amount: float

# Response schemas
class SuccessResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    message: str
    data: Optional[dict] = None

class ErrorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None

# Additional missing schemas that might be imported elsewhere
class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    company_id: int
    manager_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

class ExpenseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    amount: float
    currency: str
    category: ExpenseCategory
    description: str
    expense_date: datetime
    receipt_url: Optional[str] = None
    employee_id: int
    company_id: int
    status: ExpenseStatus
    amount_in_company_currency: float
    created_at: datetime
    updated_at: datetime

class ApprovalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    expense_id: int
    approver_id: int
    status: ExpenseStatus
    sequence: int
    comments: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

# Forgot Password schemas
class ForgotPasswordRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    email: EmailStr
    token: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=6)