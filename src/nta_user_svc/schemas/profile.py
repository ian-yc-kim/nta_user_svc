from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator


# Max lengths mirror DB column definitions
_NAME_MAX = 255
_PHONE_MAX = 50
_BIO_MAX = 1000
_OTHER_MAX = 255
_PHONE_REGEX = re.compile(r"^\+\d+$")


class ProfileBase(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    bio: Optional[str] = None
    hobby: Optional[str] = None
    occupation: Optional[str] = None
    location: Optional[str] = None

    @field_validator("name", "bio", "hobby", "occupation", "location", mode="before")
    @classmethod
    def _strip_and_truncate(cls, v, info):
        if v is None:
            return None
        s = str(v).strip()
        fname = info.field_name
        if fname == "bio":
            max_len = _BIO_MAX
        elif fname == "name":
            max_len = _NAME_MAX
        else:
            max_len = _OTHER_MAX
        if len(s) > max_len:
            s = s[:max_len]
        return s

    @field_validator("phone", mode="before")
    @classmethod
    def _validate_phone(cls, v):
        if v is None:
            return None
        s = str(v).strip()
        if len(s) > _PHONE_MAX:
            s = s[:_PHONE_MAX]
        if s == "":
            return None
        if not _PHONE_REGEX.match(s):
            raise ValueError("Invalid phone format; expected +<country_code><number>")
        return s


class ProfileCreate(ProfileBase):
    """Schema for creating profiles"""


class ProfileUpdate(ProfileBase):
    """Schema for updating profiles (partial updates allowed)"""


class ProfileOut(ProfileBase):
    id: int
    user_id: int
    email: EmailStr
    profile_photo_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProfilePublic(ProfileBase):
    id: int
    user_id: int
    profile_photo_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    # Explicitly exclude email for public view
    model_config = {"from_attributes": True}
