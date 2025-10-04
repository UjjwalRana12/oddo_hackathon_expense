from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..core.database import get_db
from ..models.models import ApprovalRule, User
from ..schemas.schemas import (
    ApprovalRule as ApprovalRuleSchema, 
    ApprovalRuleCreate
)
from ..utils.auth import get_current_user, get_admin_user

router = APIRouter()

@router.post("/", response_model=ApprovalRuleSchema)
async def create_approval_rule(
    rule_data: ApprovalRuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """
    Create a new approval rule (Admin only)
    """
    # Validate specific approver if provided
    if rule_data.specific_approver_id:
        approver = db.query(User).filter(
            User.id == rule_data.specific_approver_id,
            User.company_id == current_user.company_id,
            User.role.in_(["admin", "manager"])
        ).first()
        if not approver:
            raise HTTPException(
                status_code=400,
                detail="Invalid specific approver ID"
            )
    
    # Validate approval sequence if provided
    if rule_data.approval_sequence:
        for approver_id in rule_data.approval_sequence:
            approver = db.query(User).filter(
                User.id == approver_id,
                User.company_id == current_user.company_id,
                User.role.in_(["admin", "manager"])
            ).first()
            if not approver:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid approver ID in sequence: {approver_id}"
                )
    
    # Validate rule parameters
    if rule_data.rule_type in ["percentage", "hybrid"] and not rule_data.percentage_threshold:
        raise HTTPException(
            status_code=400,
            detail="Percentage threshold required for percentage and hybrid rules"
        )
    
    if rule_data.rule_type in ["specific_approver", "hybrid"] and not rule_data.specific_approver_id:
        raise HTTPException(
            status_code=400,
            detail="Specific approver required for specific approver and hybrid rules"
        )
    
    # Create rule
    db_rule = ApprovalRule(
        name=rule_data.name,
        company_id=current_user.company_id,
        rule_type=rule_data.rule_type,
        min_amount=rule_data.min_amount,
        max_amount=rule_data.max_amount,
        percentage_threshold=rule_data.percentage_threshold,
        specific_approver_id=rule_data.specific_approver_id,
        requires_manager_approval=rule_data.requires_manager_approval,
        approval_sequence=rule_data.approval_sequence,
        is_active=True
    )
    
    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)
    
    return db_rule

@router.get("/", response_model=List[ApprovalRuleSchema])
async def get_approval_rules(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """
    Get all approval rules for the company (Admin only)
    """
    rules = db.query(ApprovalRule).filter(
        ApprovalRule.company_id == current_user.company_id,
        ApprovalRule.is_active == True
    ).offset(skip).limit(limit).all()
    
    return rules

@router.get("/{rule_id}", response_model=ApprovalRuleSchema)
async def get_approval_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """
    Get approval rule by ID (Admin only)
    """
    rule = db.query(ApprovalRule).filter(
        ApprovalRule.id == rule_id,
        ApprovalRule.company_id == current_user.company_id
    ).first()
    
    if not rule:
        raise HTTPException(
            status_code=404,
            detail="Approval rule not found"
        )
    
    return rule

@router.put("/{rule_id}", response_model=ApprovalRuleSchema)
async def update_approval_rule(
    rule_id: int,
    rule_update: ApprovalRuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """
    Update approval rule (Admin only)
    """
    rule = db.query(ApprovalRule).filter(
        ApprovalRule.id == rule_id,
        ApprovalRule.company_id == current_user.company_id
    ).first()
    
    if not rule:
        raise HTTPException(
            status_code=404,
            detail="Approval rule not found"
        )
    
    # Validate specific approver if provided
    if rule_update.specific_approver_id:
        approver = db.query(User).filter(
            User.id == rule_update.specific_approver_id,
            User.company_id == current_user.company_id,
            User.role.in_(["admin", "manager"])
        ).first()
        if not approver:
            raise HTTPException(
                status_code=400,
                detail="Invalid specific approver ID"
            )
    
    # Update rule fields
    update_data = rule_update.dict()
    for field, value in update_data.items():
        setattr(rule, field, value)
    
    db.commit()
    db.refresh(rule)
    
    return rule

@router.delete("/{rule_id}")
async def deactivate_approval_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """
    Deactivate approval rule (Admin only)
    """
    rule = db.query(ApprovalRule).filter(
        ApprovalRule.id == rule_id,
        ApprovalRule.company_id == current_user.company_id
    ).first()
    
    if not rule:
        raise HTTPException(
            status_code=404,
            detail="Approval rule not found"
        )
    
    rule.is_active = False
    db.commit()
    
    return {"message": "Approval rule deactivated successfully"}