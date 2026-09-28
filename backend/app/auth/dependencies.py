import re

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.tokens import InvalidToken, read_user_id
from app.config import get_settings
from app.database.models import User
from app.database.session import get_db

_bearer = HTTPBearer(auto_error=False)
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(email: str) -> str:
    cleaned = email.strip().lower()
    if not _EMAIL.fullmatch(cleaned) or len(cleaned) > 320:
        raise HTTPException(status_code=422, detail="Enter a valid email address.")
    return cleaned


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: Session = Depends(get_db),
) -> User:
    settings = get_settings()
    if settings.auth_mode != "local":
        raise HTTPException(
            status_code=501,
            detail="Supabase auth is not wired in this local workspace yet.",
        )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Sign in to continue.")
    try:
        user_id = read_user_id(credentials.credentials, settings.local_auth_secret)
    except InvalidToken:
        raise HTTPException(
            status_code=401, detail="Your session expired. Sign in again."
        ) from None
    user = session.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise HTTPException(status_code=401, detail="Your session expired. Sign in again.")
    return user
