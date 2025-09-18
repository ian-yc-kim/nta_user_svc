import os
import subprocess
import logging
import pytest
from sqlalchemy.exc import IntegrityError

import nta_user_svc.config as config
from nta_user_svc.storage.files import save_profile_photo, get_full_file_path, remove_file
from nta_user_svc.services import init_profile_photo_cleanup_listeners
from nta_user_svc.models import User, Profile


def test_user_profile_crud(db_session, tmp_path, monkeypatch):
    try:
        # Ensure listeners registered for this test process
        init_profile_photo_cleanup_listeners()

        # Redirect storage to tmp path for safe file operations
        monkeypatch.setattr(config, "PROFILE_PHOTO_DIR", str(tmp_path))
        monkeypatch.setattr(config, "MAX_PHOTO_SIZE_BYTES", 200000)

        # Create user
        user = User(email="test@example.com", hashed_password="hashed")
        db_session.add(user)
        db_session.commit()
        assert user.id is not None

        # Create profile linked to user
        profile = Profile(user_id=user.id, name="Alice")
        db_session.add(profile)
        db_session.commit()
        assert profile.id is not None

        # Relationship: refresh and check
        db_session.refresh(user)
        assert user.profile is not None
        assert user.profile.name == "Alice"

        # Update and verify updated_at changed (if DB supports)
        prev_updated = user.updated_at
        user.hashed_password = "new_hashed"
        db_session.commit()
        db_session.refresh(user)
        assert user.updated_at is not None
        # updated_at may be the same value depending on DB

        # Attach a photo to profile
        # create a small image using Pillow bytes
        from PIL import Image
        import io

        img = Image.new("RGB", (5, 5), (255, 0, 0))
        bio = io.BytesIO()
        img.save(bio, format="JPEG")
        data = bio.getvalue()

        upload = type("DummyUploadFile", (), {"filename": "p.jpg", "content_type": "image/jpeg", "file": io.BytesIO(data)})()
        relative = save_profile_photo(upload, user.id)

        # attach to profile and commit
        profile.profile_photo_path = relative
        db_session.add(profile)
        db_session.commit()

        full = get_full_file_path(relative)
        assert full.exists()

        # Delete profile and ensure file is removed by listener
        db_session.delete(profile)
        db_session.commit()

        # After commit, file should no longer exist
        assert not full.exists()

        # Also verify user.profile is None
        db_session.refresh(user)
        assert user.profile is None

    except Exception as e:
        logging.error(e, exc_info=True)
        raise


def test_unique_constraints(db_session):
    # email uniqueness on users
    u1 = User(email="unique@example.com", hashed_password="h")
    db_session.add(u1)
    db_session.commit()

    u2 = User(email="unique@example.com", hashed_password="h2")
    db_session.add(u2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # user_id uniqueness on profiles
    user = User(email="user2@example.com", hashed_password="h")
    db_session.add(user)
    db_session.commit()

    p1 = Profile(user_id=user.id)
    db_session.add(p1)
    db_session.commit()

    p2 = Profile(user_id=user.id)
    db_session.add(p2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_alembic_upgrade_and_downgrade(tmp_path, monkeypatch):
    # Use a file-based sqlite DB for alembic to operate on
    db_file = tmp_path / "alembic_test.db"
    db_url = f"sqlite:///{db_file}"

    # Ensure alembic picks up this DB
    monkeypatch.setenv("DATABASE_URL", db_url)

    env = os.environ.copy()

    try:
        # Run alembic upgrade head
        res = subprocess.run(["alembic", "upgrade", "head"], check=True, capture_output=True, text=True, env=env)
        # Run alembic downgrade base
        res2 = subprocess.run(["alembic", "downgrade", "base"], check=True, capture_output=True, text=True, env=env)
    except subprocess.CalledProcessError as exc:
        logging.error("Alembic command failed", exc_info=True)
        logging.error("stdout=%s", exc.stdout)
        logging.error("stderr=%s", exc.stderr)
        raise
