import logging
import mimetypes
from pathlib import Path
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from nta_user_svc.models import Profile
from nta_user_svc.models.base import get_db
from nta_user_svc.security.jwt import get_current_user
import nta_user_svc.storage.files as storage_files
import nta_user_svc.config as config

logger = logging.getLogger(__name__)
photos_router = APIRouter()

_MIME_FALLBACK: Dict[str, str] = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


@photos_router.get("/profiles/{user_id}/photo")
def get_profile_photo(
    user_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    """Serve the profile photo for a given user_id.

    Access control: only the user themself (current_user.id == user_id) can access.
    Returns FileResponse with appropriate Content-Type and Cache-Control headers.
    """
    try:
        # Fetch profile
        try:
            stmt = select(Profile).where(Profile.user_id == user_id)
            profile = db.execute(stmt).scalars().first()
        except Exception as e:
            logger.error(e, exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

        if not profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

        # Authorization: only the owner may view their photo
        try:
            if int(current_user.id) != int(user_id):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(e, exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

        # Ensure profile has a photo path
        if not profile.profile_photo_path:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile photo not found")

        # Resolve full path safely
        try:
            full_path: Path = storage_files.get_full_file_path(profile.profile_photo_path)
        except Exception as e:
            logger.error(e, exc_info=True)
            # Treat any path resolution error as not found to avoid leaking info
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile photo not found")

        if not full_path.exists() or not full_path.is_file():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile photo not found")

        # Determine MIME type
        mime_type, _ = mimetypes.guess_type(str(full_path))
        if not mime_type:
            mime_type = _MIME_FALLBACK.get(full_path.suffix.lower(), "application/octet-stream")

        headers = {"Cache-Control": "no-cache, no-store, must-revalidate"}

        return FileResponse(path=str(full_path), media_type=mime_type, headers=headers)

    except HTTPException:
        # Re-raise known HTTP exceptions
        raise
    except Exception as e:
        logger.error(e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@photos_router.post("/profiles/{user_id}/photo/upload")
def upload_profile_photo(
    user_id: int,
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload or replace a user's profile photo.

    Atomic replacement semantics:
    - Save new file to disk first.
    - Attempt to update DB and commit.
    - If DB update fails, remove newly saved file and rollback.
    - If DB update succeeds, attempt to remove old file (log failures but do not abort).
    """
    try:
        # Authorization: only the owner may upload (admins not implemented in User model)
        try:
            if int(current_user.id) != int(user_id):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(e, exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

        # Fetch or create profile
        try:
            stmt = select(Profile).where(Profile.user_id == user_id)
            profile = db.execute(stmt).scalars().first()
        except Exception as e:
            logger.error(e, exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

        if not profile:
            # create profile record
            try:
                profile = Profile(user_id=user_id)
                db.add(profile)
                db.flush()
            except Exception as e:
                logger.error(e, exc_info=True)
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

        old_photo = profile.profile_photo_path

        # Save new file first
        try:
            new_relative = storage_files.save_profile_photo(file, user_id)
        except ValueError as ve:
            logger.error(ve, exc_info=True)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
        except Exception as e:
            logger.error(e, exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save uploaded file")

        # Attempt to update DB and commit
        try:
            profile.profile_photo_path = new_relative
            db.add(profile)
            db.commit()
            db.refresh(profile)
        except Exception as e:
            logger.error(e, exc_info=True)
            # try to cleanup newly saved file
            try:
                storage_files.remove_file(new_relative)
            except Exception as e2:
                logger.error("Failed to cleanup newly saved file after DB error", exc_info=True)
            try:
                db.rollback()
            except Exception:
                logger.error("Rollback failed after DB commit error", exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

        # DB commit succeeded. attempt to remove old file if present and different
        if old_photo and old_photo != profile.profile_photo_path:
            try:
                storage_files.remove_file(old_photo)
            except Exception as e:
                # Log but do not raise; orphaned files can be cleaned later
                logger.error("Failed to remove old profile photo: %s", old_photo, exc_info=True)

        # Return success with updated path
        return {"profile_photo_path": profile.profile_photo_path}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")
