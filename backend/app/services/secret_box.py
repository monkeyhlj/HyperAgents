from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

from app.core.config import settings


_VERSION = "v1"
_SALT_SIZE = 16
_NONCE_SIZE = 16
_MAC_SIZE = 32


def mask_secret(value: str | None) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    if len(text) <= 8:
        return f"{text[:2]}****"
    return f"{text[:4]}****{text[-4:]}"


def encrypt_secret(value: str) -> str:
    plaintext = value.encode("utf-8")
    salt = secrets.token_bytes(_SALT_SIZE)
    nonce = secrets.token_bytes(_NONCE_SIZE)
    key = _derive_key(salt)
    ciphertext = _xor_bytes(plaintext, _keystream(key, nonce, len(plaintext)))
    payload_without_mac = salt + nonce + ciphertext
    mac = hmac.new(key, payload_without_mac, hashlib.sha256).digest()
    payload = salt + nonce + mac + ciphertext
    encoded = base64.urlsafe_b64encode(payload).decode("ascii")
    return f"{_VERSION}.{encoded}"


def decrypt_secret(value: str) -> str:
    if not value.startswith(f"{_VERSION}."):
        raise ValueError("Unsupported secret payload version")

    payload = base64.urlsafe_b64decode(value.split(".", 1)[1].encode("ascii"))
    if len(payload) < _SALT_SIZE + _NONCE_SIZE + _MAC_SIZE:
        raise ValueError("Invalid secret payload")

    salt = payload[:_SALT_SIZE]
    nonce = payload[_SALT_SIZE : _SALT_SIZE + _NONCE_SIZE]
    mac = payload[_SALT_SIZE + _NONCE_SIZE : _SALT_SIZE + _NONCE_SIZE + _MAC_SIZE]
    ciphertext = payload[_SALT_SIZE + _NONCE_SIZE + _MAC_SIZE :]
    key = _derive_key(salt)
    expected_mac = hmac.new(key, salt + nonce + ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(mac, expected_mac):
        raise ValueError("Secret payload integrity check failed")
    return _xor_bytes(ciphertext, _keystream(key, nonce, len(ciphertext))).decode("utf-8")


def _derive_key(salt: bytes) -> bytes:
    secret = settings.provider_connection_secret_key.encode("utf-8")
    return hashlib.pbkdf2_hmac("sha256", secret, salt, 200_000, dklen=32)


def _keystream(key: bytes, nonce: bytes, length: int) -> bytes:
    chunks: list[bytes] = []
    counter = 0
    produced = 0
    while produced < length:
        counter_bytes = counter.to_bytes(8, "big")
        chunk = hmac.new(key, nonce + counter_bytes, hashlib.sha256).digest()
        chunks.append(chunk)
        produced += len(chunk)
        counter += 1
    return b"".join(chunks)[:length]


def _xor_bytes(left: bytes, right: bytes) -> bytes:
    return bytes(a ^ b for a, b in zip(left, right))
