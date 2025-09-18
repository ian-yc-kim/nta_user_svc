from datetime import timedelta

import pytest
import jwt as pyjwt

from nta_user_svc.models import User
from nta_user_svc.security.passwords import hash_password
from nta_user_svc.security.jwt import create_access_token
import nta_user_svc.config as config


def create_user_in_db(db_session, email: str, password: str) -> User:
    hashed = hash_password(password)
    user = User(email=email, hashed_password=hashed)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_login_success(client, db_session):
    user = create_user_in_db(db_session, "auth_success@example.com", "StrongPass123")

    resp = client.post("/api/auth/login", json={"email": "auth_success@example.com", "password": "StrongPass123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data.get("token_type") == "bearer"

    # decode token and verify payload
    token = data["access_token"]
    payload = pyjwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
    assert payload.get("user_id") == user.id


def test_login_failure_wrong_password(client, db_session):
    _ = create_user_in_db(db_session, "auth_fail@example.com", "GoodPass123")
    resp = client.post("/api/auth/login", json={"email": "auth_fail@example.com", "password": "WrongPass"})
    assert resp.status_code == 401


def test_protected_endpoint_valid_token(client, db_session):
    user = create_user_in_db(db_session, "me@example.com", "MePass123")
    # get token via login
    resp = client.post("/api/auth/login", json={"email": "me@example.com", "password": "MePass123"})
    assert resp.status_code == 200
    token = resp.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}
    r = client.get("/api/auth/me", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body.get("email") == "me@example.com"
    assert body.get("id") == user.id


def test_protected_endpoint_no_token(client):
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_protected_endpoint_invalid_token(client):
    headers = {"Authorization": "Bearer not-a-valid-token"}
    r = client.get("/api/auth/me", headers=headers)
    assert r.status_code == 401


def test_protected_endpoint_expired_token(client):
    # create expired token (expires in the past)
    token = create_access_token({"user_id": 1}, expires_delta=timedelta(seconds=-10))
    headers = {"Authorization": f"Bearer {token}"}
    r = client.get("/api/auth/me", headers=headers)
    assert r.status_code == 401


def test_protected_endpoint_token_user_not_exist(client):
    # Create token for non-existent user id
    token = create_access_token({"user_id": 9999})
    headers = {"Authorization": f"Bearer {token}"}
    r = client.get("/api/auth/me", headers=headers)
    assert r.status_code == 401
