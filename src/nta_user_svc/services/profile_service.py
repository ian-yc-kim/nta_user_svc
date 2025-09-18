from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from nta_user_svc.models import Profile, User
from nta_user_svc.schemas.profile import ProfileCreate, ProfileUpdate

logger = logging.getLogger(__name__)


class ProfileService:
    """Service encapsulating Profile CRUD operations.

    All methods accept/return SQLAlchemy model instances and will commit/rollback
    on success/error. Exceptions are logged as required by project rules.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_profile_by_user_id(self, user_id: int) -> Optional[Profile]:
        try:
            stmt = (
                select(Profile)
                .options(selectinload(Profile.user))
                .where(Profile.user_id == user_id)
            )
            result = self.db.execute(stmt)
            profile = result.scalars().one_or_none()
            return profile
        except Exception as e:
            logger.error(e, exc_info=True)
            raise

    def create_profile(self, user_id: int, profile_in: ProfileCreate) -> Profile:
        try:
            user = self.db.get(User, user_id)
            if not user:
                raise ValueError("User does not exist")

            existing = self.get_profile_by_user_id(user_id)
            if existing is not None:
                raise ValueError("Profile already exists for user")

            data = profile_in.model_dump(exclude_none=True)
            profile = Profile(user_id=user_id, **data)
            self.db.add(profile)
            self.db.commit()
            self.db.refresh(profile)
            return profile
        except ValueError:
            # domain errors - do not alter logging behavior here beyond caller's responsibility
            raise
        except Exception as e:
            try:
                self.db.rollback()
            except Exception:
                logger.error("Failed to rollback transaction after create_profile error", exc_info=True)
            logger.error(e, exc_info=True)
            raise

    def update_profile(self, profile: Profile, profile_update: ProfileUpdate) -> Profile:
        try:
            data = profile_update.model_dump(exclude_none=True)
            for key, value in data.items():
                setattr(profile, key, value)
            self.db.add(profile)
            self.db.commit()
            self.db.refresh(profile)
            return profile
        except Exception as e:
            try:
                self.db.rollback()
            except Exception:
                logger.error("Failed to rollback transaction after update_profile error", exc_info=True)
            logger.error(e, exc_info=True)
            raise

    def delete_profile(self, profile: Profile) -> None:
        try:
            self.db.delete(profile)
            # Commit so SQLAlchemy listeners (e.g., cleanup listeners) are triggered
            self.db.commit()
        except Exception as e:
            try:
                self.db.rollback()
            except Exception:
                logger.error("Failed to rollback transaction after delete_profile error", exc_info=True)
            logger.error(e, exc_info=True)
            raise
