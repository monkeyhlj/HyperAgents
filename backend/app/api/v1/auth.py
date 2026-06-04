from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id, get_db
from app.schemas.auth import TokenResponse, UserLoginRequest, UserProfile, UserRegisterRequest, UserSearchItem
from app.services.auth_utils import create_access_token
from app.services.postgres_store import store


router = APIRouter()


@router.post("/register", response_model=TokenResponse)
def register_user(payload: UserRegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = store.create_user(
        db=db,
        username=payload.username,
        password=payload.password,
        email=payload.email,
        display_name=payload.display_name,
    )
    token, expires_in = create_access_token(user.id)
    return TokenResponse(access_token=token, expires_in=expires_in, user=user)


@router.post("/login", response_model=TokenResponse)
def login_user(payload: UserLoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = store.authenticate_user(db=db, account=payload.account, password=payload.password)
    token, expires_in = create_access_token(user.id)
    return TokenResponse(access_token=token, expires_in=expires_in, user=user)


@router.get("/me", response_model=UserProfile)
def current_user_profile(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> UserProfile:
    return store.get_user_profile(db, user_id)


@router.get("/users/search", response_model=list[UserSearchItem])
def search_users(
    q: str = Query(min_length=1, max_length=80),
    limit: int = Query(default=10, ge=1, le=50),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[UserSearchItem]:
    _ = user_id
    return store.search_users(db, q=q, limit=limit)
