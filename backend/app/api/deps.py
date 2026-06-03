from fastapi import Header, HTTPException

from app.db.session import get_db_session
from app.services.auth_utils import decode_access_token


def get_current_user_id(
    authorization: str | None = Header(default=None),
    x_user_id: str | None = Header(default=None),
) -> str:
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise HTTPException(status_code=401, detail="Invalid authorization header")
        return decode_access_token(token.strip())
    return x_user_id or "demo-user"


get_db = get_db_session
