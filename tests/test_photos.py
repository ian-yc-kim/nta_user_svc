import io
import pytest
from pathlib import Path
from PIL import Image

import nta_user_svc.config as config
from nta_user_svc.storage.files import save_profile_photo, remove_file, get_full_file_path
from nta_user_svc.models import User, Profile
from nta_user_svc.security.passwords import hash_password
from nta_user_svc.security.jwt import create_access_token


class DummyUploadFile:
    def __init__(self, filename: str, content_type: str, data: bytes):
        self.filename = filename
        self.content_type = content_type
        self.file = io.BytesIO(data)


def make_image_bytes(fmt: str = "JPEG", size=(10, 10), color=(255, 0, 0)) -> bytes:
    img = Image.new("RGB", size, color)
    bio = io.BytesIO()
    img.save(bio, format=fmt)
    return bio.getvalue()


def create_user_in_db(db_session, email: str, password: str) -> User:
    hashed = hash_password(password)
    user = User(email=email, hashed_password=hashed)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_get_profile_photo_success(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROFILE_PHOTO_DIR", str(tmp_path))
    monkeypatch.setattr(config, "MAX_PHOTO_SIZE_BYTES", 200000)

    user = create_user_in_db(db_session, "photo_owner@example.com", "Pass12345")

    # save a photo
    data = make_image_bytes(fmt="JPEG")
    upload = DummyUploadFile(filename="photo.jpg", content_type="image/jpeg", data=data)
    relative = save_profile_photo(upload, user.id)

    # attach to profile
    profile = Profile(user_id=user.id, profile_photo_path=relative)
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)

    token = create_access_token({"user_id": user.id})
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get(f"/api/profiles/{user.id}/photo", headers=headers)
    assert resp.status_code == 200
    assert resp.content == data
    assert resp.headers.get("content-type") in ("image/jpeg", "image/jpg")
    assert "Cache-Control" in resp.headers

    # cleanup
    remove_file(relative)


def test_get_profile_photo_unauthenticated(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROFILE_PHOTO_DIR", str(tmp_path))

    resp = client.get(f"/api/profiles/1/photo")
    assert resp.status_code == 401


def test_get_profile_photo_forbidden(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROFILE_PHOTO_DIR", str(tmp_path))
    monkeypatch.setattr(config, "MAX_PHOTO_SIZE_BYTES", 200000)

    owner = create_user_in_db(db_session, "owner2@example.com", "Pass12345")
    other = create_user_in_db(db_session, "other@example.com", "Pass12345")

    # save a photo for owner
    data = make_image_bytes(fmt="PNG")
    upload = DummyUploadFile(filename="p.png", content_type="image/png", data=data)
    relative = save_profile_photo(upload, owner.id)
    profile = Profile(user_id=owner.id, profile_photo_path=relative)
    db_session.add(profile)
    db_session.commit()

    # authenticate as other
    token = create_access_token({"user_id": other.id})
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get(f"/api/profiles/{owner.id}/photo", headers=headers)
    assert resp.status_code == 403

    # cleanup
    remove_file(relative)


def test_get_profile_photo_no_photo(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROFILE_PHOTO_DIR", str(tmp_path))

    user = create_user_in_db(db_session, "nophoto@example.com", "Pass12345")
    profile = Profile(user_id=user.id, profile_photo_path=None)
    db_session.add(profile)
    db_session.commit()

    token = create_access_token({"user_id": user.id})
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get(f"/api/profiles/{user.id}/photo", headers=headers)
    assert resp.status_code == 404


def test_get_profile_photo_nonexistent_user(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROFILE_PHOTO_DIR", str(tmp_path))

    user = create_user_in_db(db_session, "someuser@example.com", "Pass12345")
    token = create_access_token({"user_id": user.id})
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get(f"/api/profiles/99999/photo", headers=headers)
    assert resp.status_code == 404


def test_traversal_prevention(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROFILE_PHOTO_DIR", str(tmp_path))

    user = create_user_in_db(db_session, "trav@example.com", "Pass12345")
    profile = Profile(user_id=user.id, profile_photo_path="../etc/passwd")
    db_session.add(profile)
    db_session.commit()

    token = create_access_token({"user_id": user.id})
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get(f"/api/profiles/{user.id}/photo", headers=headers)
    assert resp.status_code == 404
