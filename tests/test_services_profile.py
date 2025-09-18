from unittest.mock import patch

import pytest

from nta_user_svc.models import User, Profile
from nta_user_svc.services.profile_service import ProfileService
from nta_user_svc.schemas.profile import ProfileCreate, ProfileUpdate
from nta_user_svc.services import init_profile_photo_cleanup_listeners


def test_create_and_get_profile_success(db_session):
    user = User(email="svc1@example.com", hashed_password="pw")
    db_session.add(user)
    db_session.commit()
    svc = ProfileService(db_session)

    p_in = ProfileCreate(name="Bob", phone="+100200300")
    profile = svc.create_profile(user.id, p_in)
    assert profile.id is not None
    assert profile.user_id == user.id

    fetched = svc.get_profile_by_user_id(user.id)
    assert fetched is not None
    assert fetched.id == profile.id
    # relationship should be available
    assert fetched.user is not None
    assert fetched.user.email == user.email


def test_create_profile_user_not_found(db_session):
    svc = ProfileService(db_session)
    p_in = ProfileCreate(name="X", phone="+100")
    with pytest.raises(ValueError):
        svc.create_profile(9999, p_in)


def test_create_profile_duplicate_fails(db_session):
    user = User(email="svc2@example.com", hashed_password="pw")
    db_session.add(user)
    db_session.commit()

    # create first profile directly
    profile = Profile(user_id=user.id, name="First")
    db_session.add(profile)
    db_session.commit()

    svc = ProfileService(db_session)
    with pytest.raises(ValueError):
        svc.create_profile(user.id, ProfileCreate(name="Second", phone="+123"))


def test_update_profile_success(db_session):
    user = User(email="svc3@example.com", hashed_password="pw")
    db_session.add(user)
    db_session.commit()
    profile = Profile(user_id=user.id, name="Old")
    db_session.add(profile)
    db_session.commit()

    svc = ProfileService(db_session)
    upd = ProfileUpdate(name="New", bio="New bio")
    updated = svc.update_profile(profile, upd)
    assert updated.name == "New"
    assert updated.bio == "New bio"


def test_delete_profile_triggers_cleanup_listener(db_session, tmp_path, monkeypatch):
    # Ensure listener registered
    init_profile_photo_cleanup_listeners()

    user = User(email="svc4@example.com", hashed_password="pw")
    db_session.add(user)
    db_session.commit()

    profile = Profile(user_id=user.id, name="ToDelete", profile_photo_path="some/path.jpg")
    db_session.add(profile)
    db_session.commit()

    # Patch the storage removal function used by the listener
    with patch("nta_user_svc.storage.files.remove_file") as mock_remove:
        svc = ProfileService(db_session)
        svc.delete_profile(profile)
        # listener should call remove_file once with the path
        mock_remove.assert_called()

        # ensure profile is gone
        fetched = svc.get_profile_by_user_id(user.id)
        assert fetched is None
