import importlib
from datetime import timedelta, datetime

import pytest
import jwt as pyjwt


def setup_config_env(monkeypatch):
    # Ensure JWT env vars are set before importing config
    monkeypatch.setenv("JWT_SECRET", "test-secret-key")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("JWT_EXP_HOURS", "1")
    # reload config module to pick up env changes
    import nta_user_svc.config as config

    importlib.reload(config)
    return config


def test_create_access_token_default_exp(monkeypatch):
    config = setup_config_env(monkeypatch)
    # Import after config is reloaded
    from nta_user_svc.security.jwt import create_access_token

    token = create_access_token({"user_id": 123})
    assert isinstance(token, str)

    decoded = pyjwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
    assert decoded["user_id"] == 123
    assert "exp" in decoded

    # exp should be roughly now + config.JWT_EXP_HOURS
    exp_ts = int(decoded["exp"])
    now_ts = int(datetime.utcnow().timestamp())
    # allow a small delta
    assert exp_ts - now_ts <= config.JWT_EXP_HOURS * 3600 + 5


def test_create_access_token_custom_expires(monkeypatch):
    config = setup_config_env(monkeypatch)
    from nta_user_svc.security.jwt import create_access_token

    token = create_access_token({"user_id": 1}, expires_delta=timedelta(seconds=30))
    decoded = pyjwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
    exp_ts = int(decoded["exp"])
    now_ts = int(datetime.utcnow().timestamp())
    assert 0 < exp_ts - now_ts <= 35


def test_verify_token_success(monkeypatch):
    config = setup_config_env(monkeypatch)
    from nta_user_svc.security.jwt import create_access_token, verify_token

    token = create_access_token({"user_id": 55})
    payload = verify_token(token)
    assert payload["user_id"] == 55


def test_verify_token_expired_raises(monkeypatch):
    config = setup_config_env(monkeypatch)
    from nta_user_svc.security.jwt import create_access_token, verify_token

    token = create_access_token({"user_id": 2}, expires_delta=timedelta(seconds=-10))
    with pytest.raises(pyjwt.ExpiredSignatureError):
        verify_token(token)


def test_verify_token_invalid_signature(monkeypatch):
    config = setup_config_env(monkeypatch)
    from nta_user_svc.security.jwt import create_access_token, verify_token

    token = create_access_token({"user_id": 3})
    # Tamper with token by re-encoding with wrong secret
    parts = token.split('.')
    assert len(parts) == 3
    # Replace signature by signing header.payload with wrong key
    payload_segment = ".".join(parts[0:2])
    wrong_sig = pyjwt.encode(pyjwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM], options={"verify_signature": False}), "wrong-key", algorithm="HS256")
    # The above encode returns a full token; instead we build a malformed token to trigger invalid signature
    malformed_token = token + "tamper"
    with pytest.raises(pyjwt.InvalidTokenError):
        verify_token(malformed_token)


def test_verify_token_wrong_secret(monkeypatch):
    config = setup_config_env(monkeypatch)
    from nta_user_svc.security.jwt import create_access_token
    # create token with correct secret
    token = create_access_token({"user_id": 7})

    # Temporarily change config.JWT_SECRET to wrong key and reload jwt module to pick up change
    monkeypatch.setenv("JWT_SECRET", "wrong-secret")
    import nta_user_svc.config as config_mod
    importlib.reload(config_mod)

    from nta_user_svc.security import jwt as jwt_mod

    # Attempt to verify using wrong secret should raise InvalidTokenError (InvalidSignatureError)
    with pytest.raises(pyjwt.InvalidTokenError):
        jwt_mod.verify_token(token)
