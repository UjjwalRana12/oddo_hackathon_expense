from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from ..models.models import (
    Expense, Approval, ApprovalRule, User, 
    ExpenseStatus, UserRole, ApprovalRuleType  # Fixed: removed ApprovalStatus
)
from ..core.database import get_db

class ApprovalService:
    
    @staticmethod
    def create_approval_workflow(db: Session, expense: Expense) -> List[Approval]:
        """
        Create approval workflow for an expense based on company rules
        """
        approvals = []
        
        # Get applicable approval rules for the expense amount
        rules = db.query(ApprovalRule).filter(
            and_(
                ApprovalRule.company_id == expense.company_id,
                ApprovalRule.is_active == True,
                ApprovalRule.min_amount <= expense.amount_in_company_currency,
                ApprovalRule.max_amount >= expense.amount_in_company_currency
            )
        ).all()
        
        if not rules:
            # Default approval: employee's manager
            employee = db.query(User).filter(User.id == expense.employee_id).first()
            if employee and employee.manager_id:
                approval = Approval(
                    expense_id=expense.id,
                    approver_id=employee.manager_id,
                    sequence=1,
                    status=ExpenseStatus.PENDING  # Using ExpenseStatus instead of ApprovalStatus
                )
                db.add(approval)
                approvals.append(approval)
        else:
            # Apply rules
            sequence = 1
            for rule in rules:
                if rule.rule_type == ApprovalRuleType.SPECIFIC_APPROVER:
                    approval = Approval(
                        expense_id=expense.id,
                        approver_id=rule.specific_approver_id,
                        sequence=sequence,
                        status=ExpenseStatus.PENDING
                    )
                    db.add(approval)
                    approvals.append(approval)
                    sequence += 1
                
                elif rule.rule_type == ApprovalRuleType.PERCENTAGE:
                    # Create approvals for all rule approvers
                    for rule_approver in rule.rule_approvers:
                        approval = Approval(
                            expense_id=expense.id,
                            approver_id=rule_approver.approver_id,
                            sequence=sequence,
                            status=ExpenseStatus.PENDING
                        )
                        db.add(approval)
                        approvals.append(approval)
                    sequence += 1
        
        db.commit()
        return approvals
    
    @staticmethod
    def process_approval(db: Session, approval_id: int, approver_id: int, 
                        action: str, comments: Optional[str] = None) -> bool:
        """
        Process an approval action (approve/reject)
        """
        approval = db.query(Approval).filter(
            and_(
                Approval.id == approval_id,
                Approval.approver_id == approver_id,
                Approval.status == ExpenseStatus.PENDING
            )
        ).first()
        
        if not approval:
            return False
        
        # Update approval status
        approval.status = ExpenseStatus.APPROVED if action == "approve" else ExpenseStatus.REJECTED
        approval.comments = comments
        approval.approved_at = db.execute("SELECT CURRENT_TIMESTAMP").scalar()
        
        # Check if we need to update expense status
        expense = db.query(Expense).filter(Expense.id == approval.expense_id).first()
        if not expense:
            return False
        
        # Get all approvals for this expense
        all_approvals = db.query(Approval).filter(Approval.expense_id == expense.id).all()
        
        # Check if expense should be approved or rejected
        if action == "reject":
            expense.status = ExpenseStatus.REJECTED
        else:
            # Check if all required approvals are complete
            if ApprovalService._check_approval_completion(db, expense, all_approvals):
                expense.status = ExpenseStatus.APPROVED
        
        db.commit()
        return True
    
    @staticmethod
    def _check_approval_completion(db: Session, expense: Expense, approvals: List[Approval]) -> bool:
        """
        Check if approval process is complete based on rules
        """
        # Get approval rules for this expense
        rules = db.query(ApprovalRule).filter(
            and_(
                ApprovalRule.company_id == expense.company_id,
                ApprovalRule.is_active == True,
                ApprovalRule.min_amount <= expense.amount_in_company_currency,
                ApprovalRule.max_amount >= expense.amount_in_company_currency
            )
        ).all()
        
        if not rules:
            # Default: all approvals must be approved
            return all(approval.status == ExpenseStatus.APPROVED for approval in approvals)
        
        for rule in rules:
            if rule.rule_type == ApprovalRuleType.SPECIFIC_APPROVER:
                # Check if specific approver approved
                specific_approval = next(
                    (a for a in approvals if a.approver_id == rule.specific_approver_id), 
                    None
                )
                if specific_approval and specific_approval.status == ExpenseStatus.APPROVED:
                    return True
            
            elif rule.rule_type == ApprovalRuleType.PERCENTAGE:
                # Check if percentage of approvers approved
                rule_approvals = [a for a in approvals if any(
                    ra.approver_id == a.approver_id for ra in rule.rule_approvers
                )]
                if rule_approvals:
                    approved_count = sum(1 for a in rule_approvals if a.status == ExpenseStatus.APPROVED)
                    approval_percentage = (approved_count / len(rule_approvals)) * 100
                    if approval_percentage >= rule.percentage_required:
                        return True
            
            elif rule.rule_type == ApprovalRuleType.HYBRID:
                # Check both specific approver and percentage
                specific_approved = False
                if rule.specific_approver_id:
                    specific_approval = next(
                        (a for a in approvals if a.approver_id == rule.specific_approver_id), 
                        None
                    )
                    specific_approved = (specific_approval and 
                                       specific_approval.status == ExpenseStatus.APPROVED)
                
                percentage_approved = False
                if rule.percentage_required:
                    rule_approvals = [a for a in approvals if any(
                        ra.approver_id == a.approver_id for ra in rule.rule_approvers
                    )]
                    if rule_approvals:
                        approved_count = sum(1 for a in rule_approvals if a.status == ExpenseStatus.APPROVED)
                        approval_percentage = (approved_count / len(rule_approvals)) * 100
                        percentage_approved = approval_percentage >= rule.percentage_required
                
                if specific_approved or percentage_approved:
                    return True
        
        return False
    
    @staticmethod
    def get_pending_approvals(db: Session, approver_id: int) -> List[Approval]:
        """
        Get pending approvals for a specific approver
        """
        return db.query(Approval).filter(
            and_(
                Approval.approver_id == approver_id,
                Approval.status == ExpenseStatus.PENDING
            )
        ).all()
    
    @staticmethod
    def get_team_expenses(db: Session, manager_id: int) -> List[Expense]:
        """
        Get all expenses from team members for a manager
        """
        # Get all employees under this manager
        team_members = db.query(User).filter(User.manager_id == manager_id).all()
        team_member_ids = [member.id for member in team_members]
        
        if not team_member_ids:
            return []
        
        return db.query(Expense).filter(Expense.employee_id.in_(team_member_ids)).all()

# Create instance
approval_service = ApprovalService()