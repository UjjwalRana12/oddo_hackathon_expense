from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import os
from datetime import datetime

from ..core.database import get_db
from ..models.models import Expense, ExpenseCategory, User, ExpenseStatus
from ..schemas.schemas import (
    Expense as ExpenseSchema, 
    ExpenseCreate, 
    ExpenseUpdate,
    ExpenseStats,
    OCRResult
)
from ..utils.auth import get_current_user
from ..utils.file_utils import save_upload_file, validate_file_size, validate_file_type, generate_unique_filename
from ..services.currency_service import currency_service
from ..services.ocr_service import ocr_service
from ..services.approval_service import ApprovalService
from ..core.config import settings

router = APIRouter()

@router.post("/", response_model=ExpenseSchema)
async def create_expense(
    expense_data: ExpenseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new expense
    """
    # Validate category
    category = db.query(ExpenseCategory).filter(
        ExpenseCategory.id == expense_data.category_id,
        ExpenseCategory.company_id == current_user.company_id,
        ExpenseCategory.is_active == True
    ).first()
    
    if not category:
        raise HTTPException(
            status_code=400,
            detail="Invalid expense category"
        )
    
    # Convert amount to company currency
    company_currency = current_user.company.currency
    if expense_data.currency != company_currency:
        converted_amount = await currency_service.convert_currency(
            expense_data.amount, 
            expense_data.currency, 
            company_currency
        )
        if converted_amount is None:
            raise HTTPException(
                status_code=400,
                detail="Could not convert currency"
            )
    else:
        converted_amount = expense_data.amount
    
    # Create expense
    db_expense = Expense(
        amount=expense_data.amount,
        currency=expense_data.currency,
        amount_in_company_currency=converted_amount,
        description=expense_data.description,
        expense_date=expense_data.expense_date,
        receipt_url=expense_data.receipt_url,
        status=ExpenseStatus.PENDING,
        employee_id=current_user.id,
        company_id=current_user.company_id,
        category_id=expense_data.category_id
    )
    
    db.add(db_expense)
    db.flush()
    
    # Create approval workflow
    approval_service = ApprovalService(db)
    approval_service.create_approval_workflow(db_expense)
    
    db.commit()
    db.refresh(db_expense)
    
    return db_expense

@router.post("/upload-receipt", response_model=dict)
async def upload_receipt_with_ocr(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload receipt image and extract data using OCR
    """
    # Validate file
    allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/gif"]
    if not validate_file_type(file, allowed_types):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only JPEG, PNG, and GIF are allowed."
        )
    
    if not validate_file_size(file):
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {settings.max_file_size} bytes."
        )
    
    try:
        # Generate unique filename
        unique_filename = generate_unique_filename(file.filename)
        file_path = os.path.join(settings.upload_dir, unique_filename)
        
        # Save file
        await save_upload_file(file, file_path)
        
        # Process with OCR
        ocr_result = ocr_service.process_receipt(file_path)
        
        # Return OCR results with file path
        return {
            "message": "Receipt uploaded and processed successfully",
            "file_path": file_path,
            "ocr_result": ocr_result
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing receipt: {str(e)}"
        )

@router.post("/create-from-ocr", response_model=ExpenseSchema)
async def create_expense_from_ocr(
    amount: float = Form(...),
    currency: str = Form("USD"),
    description: str = Form(...),
    expense_date: str = Form(...),
    category_id: int = Form(...),
    receipt_path: str = Form(...),
    ocr_data: str = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create expense from OCR extracted data
    """
    try:
        # Parse expense date
        expense_date_obj = datetime.fromisoformat(expense_date.replace('Z', '+00:00'))
        
        # Create expense data
        expense_data = ExpenseCreate(
            amount=amount,
            currency=currency,
            description=description,
            expense_date=expense_date_obj,
            category_id=category_id,
            receipt_url=receipt_path
        )
        
        # Create expense using the existing endpoint logic
        return await create_expense(expense_data, db, current_user)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error creating expense from OCR: {str(e)}"
        )

@router.get("/", response_model=List[ExpenseSchema])
async def get_expenses(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get expenses for current user
    """
    query = db.query(Expense).filter(Expense.employee_id == current_user.id)
    
    if status:
        query = query.filter(Expense.status == status)
    
    expenses = query.order_by(Expense.created_at.desc()).offset(skip).limit(limit).all()
    return expenses

@router.get("/stats", response_model=ExpenseStats)
async def get_expense_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get expense statistics for current user
    """
    from sqlalchemy import func
    from datetime import datetime, timedelta
    
    # Total expenses
    total_expenses = db.query(Expense).filter(
        Expense.employee_id == current_user.id
    ).count()
    
    # Total amount
    total_amount_result = db.query(func.sum(Expense.amount_in_company_currency)).filter(
        Expense.employee_id == current_user.id
    ).scalar()
    total_amount = total_amount_result or 0.0
    
    # Status counts
    pending_expenses = db.query(Expense).filter(
        Expense.employee_id == current_user.id,
        Expense.status == ExpenseStatus.PENDING
    ).count()
    
    approved_expenses = db.query(Expense).filter(
        Expense.employee_id == current_user.id,
        Expense.status == ExpenseStatus.APPROVED
    ).count()
    
    rejected_expenses = db.query(Expense).filter(
        Expense.employee_id == current_user.id,
        Expense.status == ExpenseStatus.REJECTED
    ).count()
    
    # Monthly total (current month)
    start_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_total_result = db.query(func.sum(Expense.amount_in_company_currency)).filter(
        Expense.employee_id == current_user.id,
        Expense.created_at >= start_of_month
    ).scalar()
    monthly_total = monthly_total_result or 0.0
    
    return ExpenseStats(
        total_expenses=total_expenses,
        total_amount=total_amount,
        pending_expenses=pending_expenses,
        approved_expenses=approved_expenses,
        rejected_expenses=rejected_expenses,
        monthly_total=monthly_total
    )

@router.get("/{expense_id}", response_model=ExpenseSchema)
async def get_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get expense by ID
    """
    expense = db.query(Expense).filter(
        Expense.id == expense_id,
        Expense.employee_id == current_user.id
    ).first()
    
    if not expense:
        raise HTTPException(
            status_code=404,
            detail="Expense not found"
        )
    
    return expense

@router.put("/{expense_id}", response_model=ExpenseSchema)
async def update_expense(
    expense_id: int,
    expense_update: ExpenseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update expense (only if pending)
    """
    expense = db.query(Expense).filter(
        Expense.id == expense_id,
        Expense.employee_id == current_user.id
    ).first()
    
    if not expense:
        raise HTTPException(
            status_code=404,
            detail="Expense not found"
        )
    
    if expense.status != ExpenseStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail="Can only update pending expenses"
        )
    
    # Update fields
    update_data = expense_update.dict(exclude_unset=True)
    
    # Handle currency conversion if currency changed
    if "currency" in update_data or "amount" in update_data:
        new_currency = update_data.get("currency", expense.currency)
        new_amount = update_data.get("amount", expense.amount)
        
        company_currency = current_user.company.currency
        if new_currency != company_currency:
            converted_amount = await currency_service.convert_currency(
                new_amount, new_currency, company_currency
            )
            if converted_amount is None:
                raise HTTPException(
                    status_code=400,
                    detail="Could not convert currency"
                )
            update_data["amount_in_company_currency"] = converted_amount
        else:
            update_data["amount_in_company_currency"] = new_amount
    
    for field, value in update_data.items():
        setattr(expense, field, value)
    
    db.commit()
    db.refresh(expense)
    
    return expense

@router.delete("/{expense_id}")
async def delete_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete expense (only if pending)
    """
    expense = db.query(Expense).filter(
        Expense.id == expense_id,
        Expense.employee_id == current_user.id
    ).first()
    
    if not expense:
        raise HTTPException(
            status_code=404,
            detail="Expense not found"
        )
    
    if expense.status != ExpenseStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail="Can only delete pending expenses"
        )
    
    db.delete(expense)
    db.commit()
    
    return {"message": "Expense deleted successfully"}