from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..core.database import get_db
from ..models.models import Expense, Approval, User, ExpenseStatus  # Removed ApprovalStatus
from ..schemas.schemas import (
    ApprovalResponse, ApprovalAction, ExpenseResponse, 
    SuccessResponse, ExpenseStats
)
from ..utils.auth import get_current_user
from ..services.approval_service import approval_service

router = APIRouter()

@router.get("/pending", response_model=List[ApprovalResponse])
async def get_pending_approvals(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get pending approvals for the current user
    """
    try:
        pending_approvals = approval_service.get_pending_approvals(db, current_user.id)
        return pending_approvals
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching pending approvals: {str(e)}"
        )

@router.post("/{approval_id}/approve", response_model=SuccessResponse)
async def process_approval(
    approval_id: int,
    action_data: ApprovalAction,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Approve or reject an expense
    """
    try:
        success = approval_service.process_approval(
            db=db,
            approval_id=approval_id,
            approver_id=current_user.id,
            action=action_data.action,
            comments=action_data.comments
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Approval not found or already processed"
            )
        
        return SuccessResponse(
            message=f"Expense {action_data.action}d successfully",
            data={"approval_id": approval_id, "action": action_data.action}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing approval: {str(e)}"
        )

@router.get("/team-expenses", response_model=List[ExpenseResponse])
async def get_team_expenses(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get expenses from team members (for managers)
    """
    try:
        if current_user.role not in ["manager", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only managers and admins can view team expenses"
            )
        
        team_expenses = approval_service.get_team_expenses(db, current_user.id)
        return team_expenses
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching team expenses: {str(e)}"
        )

@router.get("/stats", response_model=ExpenseStats)
async def get_approval_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get approval statistics for the current user
    """
    try:
        if current_user.role not in ["manager", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only managers and admins can view approval statistics"
            )
        
        # Get pending approvals count
        pending_approvals = approval_service.get_pending_approvals(db, current_user.id)
        pending_count = len(pending_approvals)
        
        # Get team expenses if manager
        team_expenses = approval_service.get_team_expenses(db, current_user.id)
        
        approved_count = len([e for e in team_expenses if e.status == ExpenseStatus.APPROVED])
        rejected_count = len([e for e in team_expenses if e.status == ExpenseStatus.REJECTED])
        
        total_amount = sum(e.amount_in_company_currency for e in team_expenses)
        approved_amount = sum(e.amount_in_company_currency for e in team_expenses if e.status == ExpenseStatus.APPROVED)
        rejected_amount = sum(e.amount_in_company_currency for e in team_expenses if e.status == ExpenseStatus.REJECTED)
        pending_amount = sum(e.amount_in_company_currency for e in team_expenses if e.status == ExpenseStatus.PENDING)
        
        return ExpenseStats(
            total_expenses=len(team_expenses),
            total_amount=total_amount,
            pending_count=pending_count,
            approved_count=approved_count,
            rejected_count=rejected_count,
            pending_amount=pending_amount,
            approved_amount=approved_amount,
            rejected_amount=rejected_amount
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching approval statistics: {str(e)}"
        )