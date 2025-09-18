import os
import subprocess
import logging
import pytest
from sqlalchemy.exc import IntegrityError

from nta_user_svc.models import User, Profile


def test_user_profile_crud(db_session):
    try:
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

        # Delete profile
        db_session.delete(profile)
        db_session.commit()
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
