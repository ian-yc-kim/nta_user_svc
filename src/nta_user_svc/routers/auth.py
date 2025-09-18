import logging
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from nta_user_svc.models.base import get_db
from nta_user_svc.models import User
from nta_user_svc.security.passwords import verify_password
from nta_user_svc.security import create_access_token, get_current_user

logger = logging.getLogger(__name__)

auth_router = APIRouter()


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


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
