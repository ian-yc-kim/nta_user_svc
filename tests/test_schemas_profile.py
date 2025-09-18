from datetime import datetime

import pytest
from pydantic import ValidationError

from nta_user_svc.schemas.profile import (
    ProfileCreate,
    ProfileUpdate,
    ProfileOut,
    ProfilePublic,
)

from nta_user_svc.models import User, Profile


def test_valid_profile_create_trims_and_truncates():
    long_name = "  " + "A" * 300 + "  "
    bio = "  Some bio "
    p = ProfileCreate(name=long_name, bio=bio, phone="+1234567890", hobby=" hobby ")
    assert p.name == "A" * 255
    assert p.bio == "Some bio"
    assert p.hobby == "hobby"
    assert p.phone == "+1234567890"


def test_invalid_phone_raises():
    with pytest.raises(ValidationError):
        ProfileCreate(phone="12345")
    with pytest.raises(ValidationError):
        ProfileCreate(phone="+12 345")
    with pytest.raises(ValidationError):
        ProfileCreate(phone="+12a34")


def test_string_whitespace_stripping_and_max_length():
    # name max 255, bio max 1000
    name = "  John Doe  "
    bio = "  " + ("b" * 1200) + "  "
    p = ProfileCreate(name=name, bio=bio)
    assert p.name == "John Doe"
    assert len(p.bio) == 1000


def _make_profile_with_user(db_session):
    user = User(email="u@example.com", hashed_password="x")
    db_session.add(user)
    db_session.commit()
    profile = Profile(user_id=user.id, name="Alice")
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)
    db_session.refresh(user)
    # expose email attr on profile so pydantic from_attributes picks it up
    setattr(profile, "email", user.email)
    return profile


def test_profile_out_includes_email(db_session):
    profile = _make_profile_with_user(db_session)
    out = ProfileOut.model_validate(profile)
    # compare raw strings to avoid depending on EmailStr construction semantics
    assert out.email == profile.email
    assert out.id == profile.id


def test_profile_public_excludes_email(db_session):
    profile = _make_profile_with_user(db_session)
    pub = ProfilePublic.model_validate(profile)
    # ProfilePublic should not have 'email' field
    assert not hasattr(pub, "email")
    assert pub.id == profile.id
