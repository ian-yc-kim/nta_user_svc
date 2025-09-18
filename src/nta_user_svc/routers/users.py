import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from nta_user_svc.database import get_db
from nta_user_svc.security.jwt import get_current_user
from nta_user_svc.services import ProfileService
from nta_user_svc.schemas.profile import (
    ProfileCreate,
    ProfileUpdate,
    ProfileOut,
    ProfilePublic,
)
from nta_user_svc.models import User

logger = logging.getLogger(__name__)
users_router = APIRouter()


def get_profile_service(db: Session = Depends(get_db)) -> ProfileService:
    """Factory dependency that provides a ProfileService bound to the request DB session."""
    return ProfileService(db)


@users_router.post(
    "/profiles",
    status_code=status.HTTP_201_CREATED,
    response_model=ProfileOut,
)
def create_profile(
    profile_in: ProfileCreate,
    current_user: User = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service),
) -> ProfileOut:
    try:
        # Check whether profile already exists for current user
        try:
            existing = profile_service.get_profile_by_user_id(current_user.id)
        except Exception as e:
            logger.error(e, exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

        if existing is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Profile already exists")

        try:
            profile = profile_service.create_profile(current_user.id, profile_in)
        except ValueError as ve:
            # Domain errors from service
            msg = str(ve)
            if "User does not exist" in msg:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
            if "Profile already exists" in msg:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=msg)
            # Other value errors map to bad request
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
        except Exception as e:
            logger.error(e, exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

        # Ensure email field is present on returned object for ProfileOut
        try:
            setattr(profile, "email", current_user.email)
            return ProfileOut.model_validate(profile)
        except Exception as e:
            logger.error(e, exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@users_router.get(
    "/users/me/profile",
    response_model=ProfileOut,
)
def get_own_profile(
    current_user: User = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service),
) -> ProfileOut:
    try:
        try:
            profile = profile_service.get_profile_by_user_id(current_user.id)
        except Exception as e:
            logger.error(e, exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

        if not profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

        try:
            # Ensure returned profile includes the user's email
            setattr(profile, "email", current_user.email)
            return ProfileOut.model_validate(profile)
        except Exception as e:
            logger.error(e, exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@users_router.get(
    "/profiles/{user_id}",
    response_model=ProfilePublic,
)
def get_public_profile(
    user_id: int,
    current_user: User = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service),
) -> ProfilePublic:
    try:
        try:
            profile = profile_service.get_profile_by_user_id(user_id)
        except Exception as e:
            logger.error(e, exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

        if not profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

        try:
            # For public profile, do not include email. ProfilePublic excludes email by schema.
            return ProfilePublic.model_validate(profile)
        except Exception as e:
            logger.error(e, exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@users_router.put(
    "/profiles/me",
    response_model=ProfileOut,
)
def update_own_profile(
    profile_in: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service),
) -> ProfileOut:
    try:
        try:
            profile = profile_service.get_profile_by_user_id(current_user.id)
        except Exception as e:
            logger.error(e, exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

        if not profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

        try:
            updated = profile_service.update_profile(profile, profile_in)
        except Exception as e:
            logger.error(e, exc_info=True)
            # Service layer handles rollback; map to 500
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

        try:
            setattr(updated, "email", current_user.email)
            return ProfileOut.model_validate(updated)
        except Exception as e:
            logger.error(e, exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@users_router.delete(
    "/profiles/me",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_own_profile(
    current_user: User = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service),
) -> None:
    try:
        try:
            profile = profile_service.get_profile_by_user_id(current_user.id)
        except Exception as e:
            logger.error(e, exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

        if not profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

        try:
            profile_service.delete_profile(profile)
            return None
        except Exception as e:
            logger.error(e, exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")
