import logging
import mimetypes
from pathlib import Path
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from nta_user_svc.models import Profile
from nta_user_svc.models.base import get_db
from nta_user_svc.security.jwt import get_current_user
import nta_user_svc.storage.files as storage_files

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
