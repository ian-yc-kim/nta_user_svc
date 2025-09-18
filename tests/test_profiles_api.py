from nta_user_svc.models import User, Profile
from nta_user_svc.security.jwt import create_access_token
from nta_user_svc.security.passwords import hash_password


def _create_user_and_token(db_session, email: str = "u@example.com"):
    hashed = hash_password("TestPass123")
    user = User(email=email, hashed_password=hashed)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    token = create_access_token({"user_id": user.id})
    return user, token


def test_create_profile_success(client, db_session):
    user, token = _create_user_and_token(db_session, "create@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"name": "Alice", "phone": "+100200300"}

    r = client.post("/api/profiles", json=payload, headers=headers)
    assert r.status_code == 201
    data = r.json()
    assert data.get("email") == user.email

    # verify in DB
    p = db_session.query(Profile).filter_by(user_id=user.id).first()
    assert p is not None
    assert p.name == "Alice"


def test_get_own_profile(client, db_session):
    user, token = _create_user_and_token(db_session, "own@example.com")
    # create profile directly
    profile = Profile(user_id=user.id, name="Owner", phone="+111111")
    db_session.add(profile)
    db_session.commit()

    headers = {"Authorization": f"Bearer {token}"}
    r = client.get("/api/users/me/profile", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data.get("email") == user.email
    assert data.get("name") == "Owner"


def test_get_public_profile_excludes_email(client, db_session):
    user_a, _ = _create_user_and_token(db_session, "public_a@example.com")
    # create profile for user_a
    profile = Profile(user_id=user_a.id, name="PublicA", phone="+222222")
    db_session.add(profile)
    db_session.commit()

    # another user who will fetch public profile
    user_b, token_b = _create_user_and_token(db_session, "public_b@example.com")
    headers = {"Authorization": f"Bearer {token_b}"}

    r = client.get(f"/api/profiles/{user_a.id}", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert "email" not in data
    assert data.get("name") == "PublicA"


def test_update_profile_success(client, db_session):
    user, token = _create_user_and_token(db_session, "upd@example.com")
    profile = Profile(user_id=user.id, name="Before", phone="+333333")
    db_session.add(profile)
    db_session.commit()

    headers = {"Authorization": f"Bearer {token}"}
    payload = {"bio": "New bio"}
    r = client.put("/api/profiles/me", json=payload, headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data.get("bio") == "New bio"

    # persisted
    p = db_session.query(Profile).filter_by(user_id=user.id).first()
    assert p.bio == "New bio"


def test_delete_profile_success(client, db_session):
    user, token = _create_user_and_token(db_session, "del@example.com")
    profile = Profile(user_id=user.id, name="ToDelete")
    db_session.add(profile)
    db_session.commit()

    headers = {"Authorization": f"Bearer {token}"}
    r = client.delete("/api/profiles/me", headers=headers)
    assert r.status_code == 204

    p = db_session.query(Profile).filter_by(user_id=user.id).first()
    assert p is None


def test_unauthorized_no_token(client, db_session):
    # POST
    r = client.post("/api/profiles", json={"name": "X"})
    assert r.status_code == 401
    # GET own
    r = client.get("/api/users/me/profile")
    assert r.status_code == 401
    # GET public
    r = client.get("/api/profiles/1")
    assert r.status_code == 401
    # PUT
    r = client.put("/api/profiles/me", json={"bio": "x"})
    assert r.status_code == 401
    # DELETE
    r = client.delete("/api/profiles/me")
    assert r.status_code == 401


def test_validation_errors_for_post_and_put(client, db_session):
    user, token = _create_user_and_token(db_session, "val@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # invalid phone on POST
    r = client.post("/api/profiles", json={"phone": "12345"}, headers=headers)
    assert r.status_code == 422

    # create profile first (directly)
    profile = Profile(user_id=user.id, name="V")
    db_session.add(profile)
    db_session.commit()

    # invalid phone on PUT
    r = client.put("/api/profiles/me", json={"phone": "abc"}, headers=headers)
    assert r.status_code == 422


def test_profile_not_found_scenarios(client, db_session):
    # user without profile
    user, token = _create_user_and_token(db_session, "nofind@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    r = client.get("/api/users/me/profile", headers=headers)
    assert r.status_code == 404

    r = client.put("/api/profiles/me", json={"bio": "x"}, headers=headers)
    assert r.status_code == 404

    r = client.delete("/api/profiles/me", headers=headers)
    assert r.status_code == 404

    # public profile for non-existent user
    # create another user to authenticate
    other, token2 = _create_user_and_token(db_session, "other@example.com")
    headers2 = {"Authorization": f"Bearer {token2}"}
    r = client.get("/api/profiles/9999", headers=headers2)
    assert r.status_code == 404


def test_post_profile_already_exists(client, db_session):
    user, token = _create_user_and_token(db_session, "exists@example.com")
    # create profile directly
    profile = Profile(user_id=user.id, name="Exists")
    db_session.add(profile)
    db_session.commit()

    headers = {"Authorization": f"Bearer {token}"}
    r = client.post("/api/profiles", json={"name": "New"}, headers=headers)
    assert r.status_code == 409
