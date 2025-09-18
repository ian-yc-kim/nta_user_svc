from nta_user_svc.security.passwords import (
    hash_password,
    verify_password,
    validate_password_strength,
)


def test_hash_password_generates_unique_hashes_for_same_input():
    pw = "StrongPass123"
    h1 = hash_password(pw)
    h2 = hash_password(pw)
    assert isinstance(h1, str)
    assert isinstance(h2, str)
    # Due to unique salts, hashes should differ for the same password
    assert h1 != h2
    # Both hashes should verify correctly
    assert verify_password(pw, h1)
    assert verify_password(pw, h2)


def test_verify_password_success_and_failure():
    pw = "AnotherPass1"
    hashed = hash_password(pw)
    assert verify_password(pw, hashed) is True
    assert verify_password("wrongpass", hashed) is False
    # Non-string inputs should be handled gracefully and return False
    assert verify_password(12345, hashed) is False
    assert verify_password(pw, 12345) is False


def test_validate_password_strength_variations():
    # too short
    msg = validate_password_strength("short1")
    assert isinstance(msg, str) and "at least 8" in msg

    # no letters
    msg = validate_password_strength("12345678")
    assert isinstance(msg, str) and "letter" in msg

    # no numbers
    msg = validate_password_strength("abcdefgh")
    assert isinstance(msg, str) and "number" in msg

    # valid password
    assert validate_password_strength("Abcdefg1") is None

    # non-string input
    msg = validate_password_strength(12345678)
    assert isinstance(msg, str) and "string" in msg
