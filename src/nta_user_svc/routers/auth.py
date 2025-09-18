import logging
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from nta_user_svc.models.base import get_db
from nta_user_svc.models import User, Profile
from nta_user_svc.security.passwords import verify_password, validate_password_strength, hash_password
from nta_user_svc.security import create_access_token, get_current_user

logger = logging.getLogger(__name__)

auth_router = APIRouter()


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: EmailStr
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


@auth_router.post("/auth/login", response_model=Token)
def login(user_credentials: UserLogin, db: Session = Depends(get_db)) -> Token:
    """Authenticate user and issue JWT access token."""
    try:
        stmt = select(User).where(User.email == user_credentials.email)
        user = db.execute(stmt).scalars().first()
    except Exception as e:
        logger.error(e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

    if not user:
        # Do not reveal whether the email exists
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    try:
        if not verify_password(user_credentials.password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

    # Create token payload
    try:
        token = create_access_token({"user_id": user.id})
    except Exception as e:
        logger.error(e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create access token")

    return Token(access_token=token, token_type="bearer")


@auth_router.get("/auth/me")
def read_current_user(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """Return basic information about the authenticated user."""
    try:
        return {"id": current_user.id, "email": current_user.email}
    except Exception as e:
        logger.error(e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@auth_router.post(
    "/auth/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
)
def register_user(user_in: UserCreate, db: Session = Depends(get_db)) -> User:
    """Register a new user and create an associated Profile in the same transaction."""
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

        # Create user and profile together using relationship so SQLAlchemy can persist FK
        user = User(email=user_in.email, hashed_password=hashed)
        profile = Profile(user=user)

        db.add(user)
        db.add(profile)

        try:
            db.commit()
            # Refresh to populate attributes
            db.refresh(user)
            db.refresh(profile)
        except IntegrityError as e:
            # Likely duplicate email or unique constraint on profile.user_id
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
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Ensure rollback on unexpected errors and log
        try:
            db.rollback()
        except Exception:
            logger.error("Failed to rollback after unexpected error", exc_info=True)
        logger.error(e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")
