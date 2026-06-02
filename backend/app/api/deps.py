from fastapi import Header

from app.db.session import get_db_session


def get_current_user_id(x_user_id: str | None = Header(default=None)) -> str:
    return x_user_id or "demo-user"


get_db = get_db_session
