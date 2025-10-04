from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..core.database import get_db
from ..models.models import User, Company
from ..schemas.schemas import User as UserSchema, UserCreate, UserUpdate
from ..utils.auth import get_current_user, get_admin_user
from ..core.security import get_password_hash

router = APIRouter()

@router.post("/", response_model=UserSchema)
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """
    Create a new user (Admin only)
    """
    # Check if user already exists
    db_user = db.query(User).filter(User.email == user_data.email).first()
    if db_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    # Validate manager if provided
    if user_data.manager_id:
        manager = db.query(User).filter(
            User.id == user_data.manager_id,
            User.company_id == current_user.company_id,
            User.role.in_(["admin", "manager"])
        ).first()
        if not manager:
            raise HTTPException(
                status_code=400,
                detail="Invalid manager ID"
            )
    
    # Create user
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        role=user_data.role,
        company_id=current_user.company_id,
        manager_id=user_data.manager_id,
        is_active=True
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user

@router.get("/", response_model=List[UserSchema])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """
    Get all users in the company (Admin only)
    """
    users = db.query(User).filter(
        User.company_id == current_user.company_id
    ).offset(skip).limit(limit).all()
    
    return users

@router.get("/me", response_model=UserSchema)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current user information
    """
    return current_user

@router.get("/{user_id}", response_model=UserSchema)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get user by ID
    """
    # Admin can see any user, others can only see themselves
    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(
            status_code=403,
            detail="Not enough permissions"
        )
    
    user = db.query(User).filter(
        User.id == user_id,
        User.company_id == current_user.company_id
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    
    return user

@router.put("/{user_id}", response_model=UserSchema)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """
    Update user (Admin only)
    """
    user = db.query(User).filter(
        User.id == user_id,
        User.company_id == current_user.company_id
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    
    # Validate manager if provided
    if user_update.manager_id:
        manager = db.query(User).filter(
            User.id == user_update.manager_id,
            User.company_id == current_user.company_id,
            User.role.in_(["admin", "manager"])
        ).first()
        if not manager:
            raise HTTPException(
                status_code=400,
                detail="Invalid manager ID"
            )
    
    # Update user fields
    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    
    return user

@router.delete("/{user_id}")
async def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """
    Deactivate user (Admin only)
    """
    user = db.query(User).filter(
        User.id == user_id,
        User.company_id == current_user.company_id
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    
    if user.id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="Cannot deactivate yourself"
        )
    
    user.is_active = False
    db.commit()
    
    return {"message": "User deactivated successfully"}

@router.get("/managers/list", response_model=List[UserSchema])
async def get_managers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all managers in the company
    """
    managers = db.query(User).filter(
        User.company_id == current_user.company_id,
        User.role.in_(["admin", "manager"]),
        User.is_active == True
    ).all()
    
    return managers