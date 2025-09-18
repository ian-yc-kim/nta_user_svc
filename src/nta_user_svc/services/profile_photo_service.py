import logging
from typing import Callable

from sqlalchemy import event

logger = logging.getLogger(__name__)

_listeners_registered = False


def _cleanup_profile_photo_on_delete(mapper, connection, target) -> None:
    """SQLAlchemy before_delete listener to remove profile photo file from storage.

    This intentionally catches and logs all exceptions to avoid interfering with the
    database deletion transaction (prioritize DB consistency).
    """
    try:
        # local import to avoid circular imports
        from nta_user_svc.storage import files as storage_files

        path = getattr(target, "profile_photo_path", None)
        if not path:
            return

        try:
            storage_files.remove_file(path)
        except Exception as e:
            logger.error("Failed to remove profile photo during delete: %s", path, exc_info=True)
            # swallow the exception to not block DB delete
    except Exception as e:
        logger.error("Unexpected error in cleanup listener", exc_info=True)
        # swallow to avoid breaking delete


def init_profile_photo_cleanup_listeners() -> None:
    """Register SQLAlchemy event listeners for Profile deletes.

    This function is idempotent and safe to call multiple times.
    """
    global _listeners_registered
    if _listeners_registered:
        return

    try:
        # local import to avoid import cycles at package import time
        from nta_user_svc.models import Profile

        # Register the before_delete listener for Profile
        event.listen(Profile, "before_delete", _cleanup_profile_photo_on_delete)
        _listeners_registered = True
    except Exception as e:
        logger.error("Failed to initialize profile photo cleanup listeners", exc_info=True)
        raise
