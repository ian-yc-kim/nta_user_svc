import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from nta_user_svc.models.base import get_db
from nta_user_svc.models import User
from nta_user_svc.security.passwords import (
    validate_password_strength,
    hash_password,
)

logger = logging.getLogger(__name__)

users_router = APIRouter()


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: EmailStr
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


@users_router.post(
    "/users/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
)
def register_user(user_in: UserCreate, db: Session = Depends(get_db)) -> User:
    """Register a new user.

    - Validate password strength
    - Hash password
    - Persist User (handle unique email constraint)
    - Return created user (without password)
    """
    try:
        # Validate password strength
        pw_err = validate_password_strength(user_in.password)
        if pw_err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=pw_err)

        # Hash the password
        try:
            hashed = hash_password(user_in.password)
        except Exception as e:
            logger.error(e, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process password",
            )

        # Create user model and persist
        user = User(email=user_in.email, hashed_password=hashed)
        db.add(user)
        try:
            db.commit()
            db.refresh(user)
        except IntegrityError as e:
            # Likely duplicate email
            try:
                db.rollback()
            except Exception:
                logger.error("Failed to rollback after IntegrityError", exc_info=True)
            logger.error(e, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Email already registered."
            )

        return user

    except HTTPException:
        # Re-raise HTTP exceptions (already logged where appropriate)
        raise
    except Exception as e:
        logger.error(e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
