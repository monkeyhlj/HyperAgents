from app.services.auth_utils import create_access_token, decode_access_token, hash_password, verify_password


def test_password_hash_and_verify() -> None:
    hashed = hash_password("secret123")
    assert hashed != "secret123"
    assert verify_password("secret123", hashed)
    assert not verify_password("bad-pass", hashed)


def test_access_token_roundtrip() -> None:
    token, expires_in = create_access_token("user-123")
    assert expires_in > 0
    user_id = decode_access_token(token)
    assert user_id == "user-123"
