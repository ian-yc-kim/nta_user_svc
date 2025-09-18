from nta_user_svc.models import User, Profile
from nta_user_svc.security.passwords import verify_password


def test_register_success(client, db_session):
    payload = {"email": "test@example.com", "password": "StrongPass123"}
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data.get("email") == "test@example.com"
    assert "id" in data
    # Ensure no plain password is returned
    assert "password" not in data
    assert "hashed_password" not in data

    # Verify stored password is hashed and verifies
    user = db_session.query(User).filter_by(email="test@example.com").first()
    assert user is not None
    assert user.hashed_password != payload["password"]
    assert verify_password(payload["password"], user.hashed_password) is True

    # Verify a Profile was created for the new user
    profile = db_session.query(Profile).filter_by(user_id=user.id).first()
    assert profile is not None


def test_register_weak_passwords(client):
    cases = [
        ("short1", "at least 8"),
        ("12345678", "letter"),
        ("abcdefgh", "number"),
    ]
    for pw, expected_substr in cases:
        payload = {"email": f"weak{pw}@example.com", "password": pw}
        resp = client.post("/api/auth/register", json=payload)
        assert resp.status_code == 400
        # detail may be a string
        detail = resp.json().get("detail", "")
        assert expected_substr in detail


def test_register_duplicate_email(client):
    payload = {"email": "dup@example.com", "password": "DupPass123"}
    r1 = client.post("/api/auth/register", json=payload)
    assert r1.status_code == 201

    r2 = client.post("/api/auth/register", json=payload)
    assert r2.status_code == 409
    assert "Email already registered" in r2.json().get("detail", "")
