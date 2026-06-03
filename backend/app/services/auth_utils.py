import base64
import hashlib
import hmac
import json
import secrets
import time

from fastapi import HTTPException

from app.core.config import settings

_PASSWORD_ALGO = "pbkdf2_sha256"
_PASSWORD_ITERATIONS = 120000


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(raw: str) -> bytes:
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw + padding)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        _PASSWORD_ITERATIONS,
    )
    return f"{_PASSWORD_ALGO}${_PASSWORD_ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        algo, iterations, salt, hex_digest = encoded_hash.split("$", 3)
        if algo != _PASSWORD_ALGO:
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations),
        )
        return hmac.compare_digest(digest.hex(), hex_digest)
    except ValueError:
        return False


def create_access_token(user_id: str) -> tuple[str, int]:
    exp = int(time.time()) + settings.auth_token_expire_minutes * 60
    payload = {"sub": user_id, "exp": exp}
    payload_json = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    payload_b64 = _b64url_encode(payload_json)
    sig = hmac.new(
        settings.auth_secret_key.encode("utf-8"),
        payload_b64.encode("ascii"),
        hashlib.sha256,
    ).digest()
    token = f"ha1.{payload_b64}.{_b64url_encode(sig)}"
    return token, settings.auth_token_expire_minutes * 60


def decode_access_token(token: str) -> str:
    parts = token.split(".")
    if len(parts) != 3 or parts[0] != "ha1":
        raise HTTPException(status_code=401, detail="Invalid token")

    payload_b64 = parts[1]
    signature_b64 = parts[2]
    expected_sig = hmac.new(
        settings.auth_secret_key.encode("utf-8"),
        payload_b64.encode("ascii"),
        hashlib.sha256,
    ).digest()
    provided_sig = _b64url_decode(signature_b64)
    if not hmac.compare_digest(expected_sig, provided_sig):
        raise HTTPException(status_code=401, detail="Invalid token signature")

    try:
        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=401, detail="Invalid token payload") from exc

    sub = payload.get("sub")
    exp = payload.get("exp")
    if not isinstance(sub, str) or not sub:
        raise HTTPException(status_code=401, detail="Invalid token subject")
    if not isinstance(exp, int) or exp <= int(time.time()):
        raise HTTPException(status_code=401, detail="Token has expired")
    return sub
