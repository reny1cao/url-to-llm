"""User management endpoints."""

from typing import Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field, validator

from ..dependencies import get_user_repository
from ..models.auth import User
from ..repositories.users import UserRepository
from ..services.auth import get_current_user

logger = structlog.get_logger()
router = APIRouter(prefix="/users", tags=["Users"])

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserCreate(BaseModel):
    """User registration request."""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100, pattern="^[a-zA-Z0-9_-]+$")
    password: str = Field(..., min_length=8, max_length=100)
    
    @validator('password')
    def validate_password(cls, v):
        """Ensure password meets security requirements."""
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserResponse(BaseModel):
    """User response model."""
    id: UUID
    email: str
    username: str
    is_active: bool
    is_superuser: bool
    created_at: str
    
    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """User update request."""
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=100, pattern="^[a-zA-Z0-9_-]+$")
    is_active: Optional[bool] = None


class PasswordChange(BaseModel):
    """Password change request."""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)
    
    @validator('new_password')
    def validate_password(cls, v, values):
        """Ensure new password meets requirements and differs from current."""
        if 'current_password' in values and v == values['current_password']:
            raise ValueError('New password must be different from current password')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    user_repo: UserRepository = Depends(get_user_repository)
):
    """Register a new user."""
    # Check if user already exists
    existing_user = await user_repo.get_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    existing_user = await user_repo.get_by_username(user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # Hash password
    hashed_password = pwd_context.hash(user_data.password)
    
    # Create user
    user = await user_repo.create_user(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hashed_password
    )
    
    logger.info("User registered", user_id=str(user.id), username=user.username)
    
    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        created_at=user.created_at.isoformat()
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """Get current user's profile."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        created_at=current_user.created_at.isoformat()
    )


@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repository)
):
    """Update current user's profile."""
    # Check if email is being changed and already exists
    if user_update.email and user_update.email != current_user.email:
        existing_user = await user_repo.get_by_email(user_update.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use"
            )
    
    # Check if username is being changed and already exists
    if user_update.username and user_update.username != current_user.username:
        existing_user = await user_repo.get_by_username(user_update.username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
    
    # Update user
    updated_user = await user_repo.update_user(
        user_id=current_user.id,
        email=user_update.email,
        username=user_update.username,
        is_active=user_update.is_active
    )
    
    logger.info("User profile updated", user_id=str(current_user.id))
    
    return UserResponse(
        id=updated_user.id,
        email=updated_user.email,
        username=updated_user.username,
        is_active=updated_user.is_active,
        is_superuser=updated_user.is_superuser,
        created_at=updated_user.created_at.isoformat()
    )


@router.post("/me/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repository)
):
    """Change current user's password."""
    # Verify current password
    if not pwd_context.verify(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password"
        )
    
    # Hash new password
    hashed_password = pwd_context.hash(password_data.new_password)
    
    # Update password
    await user_repo.update_password(current_user.id, hashed_password)
    
    logger.info("User password changed", user_id=str(current_user.id))
    
    return


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_current_user(
    current_user: User = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repository)
):
    """Delete current user's account."""
    await user_repo.delete_user(current_user.id)
    
    logger.info("User account deleted", user_id=str(current_user.id))
    
    return


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repository)
):
    """Get user by ID (admin only)."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        )
    
    user = await user_repo.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        created_at=user.created_at.isoformat()
    )