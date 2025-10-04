from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..core.database import get_db
from ..models.models import ExpenseCategory, User
from ..schemas.schemas import (
    ExpenseCategory as ExpenseCategorySchema, 
    ExpenseCategoryCreate
)
from ..utils.auth import get_current_user, get_admin_user

router = APIRouter()

@router.post("/", response_model=ExpenseCategorySchema)
async def create_expense_category(
    category_data: ExpenseCategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """
    Create a new expense category (Admin only)
    """
    db_category = ExpenseCategory(
        name=category_data.name,
        description=category_data.description,
        company_id=current_user.company_id,
        is_active=True
    )
    
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    
    return db_category

@router.get("/", response_model=List[ExpenseCategorySchema])
async def get_expense_categories(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all expense categories for the company
    """
    categories = db.query(ExpenseCategory).filter(
        ExpenseCategory.company_id == current_user.company_id,
        ExpenseCategory.is_active == True
    ).offset(skip).limit(limit).all()
    
    return categories

@router.get("/{category_id}", response_model=ExpenseCategorySchema)
async def get_expense_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get expense category by ID
    """
    category = db.query(ExpenseCategory).filter(
        ExpenseCategory.id == category_id,
        ExpenseCategory.company_id == current_user.company_id
    ).first()
    
    if not category:
        raise HTTPException(
            status_code=404,
            detail="Expense category not found"
        )
    
    return category

@router.put("/{category_id}", response_model=ExpenseCategorySchema)
async def update_expense_category(
    category_id: int,
    category_update: ExpenseCategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """
    Update expense category (Admin only)
    """
    category = db.query(ExpenseCategory).filter(
        ExpenseCategory.id == category_id,
        ExpenseCategory.company_id == current_user.company_id
    ).first()
    
    if not category:
        raise HTTPException(
            status_code=404,
            detail="Expense category not found"
        )
    
    category.name = category_update.name
    category.description = category_update.description
    
    db.commit()
    db.refresh(category)
    
    return category

@router.delete("/{category_id}")
async def deactivate_expense_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """
    Deactivate expense category (Admin only)
    """
    category = db.query(ExpenseCategory).filter(
        ExpenseCategory.id == category_id,
        ExpenseCategory.company_id == current_user.company_id
    ).first()
    
    if not category:
        raise HTTPException(
            status_code=404,
            detail="Expense category not found"
        )
    
    category.is_active = False
    db.commit()
    
    return {"message": "Expense category deactivated successfully"}