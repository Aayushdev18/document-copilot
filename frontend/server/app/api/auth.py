import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, normalize_email
from app.auth.tokens import issue_token
from app.config import get_settings
from app.database.models import User
from app.database.session import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


class SessionRequest(BaseModel):
    email: str


class SessionResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    token: str
    email: str
    user_id: str = Field(serialization_alias="userId")


class UserResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    email: str
    user_id: str = Field(serialization_alias="userId")


@router.post("/session", response_model=SessionResponse)
async def create_session(
    body: SessionRequest, session: Session = Depends(get_db)
) -> SessionResponse:
    settings = get_settings()
    if settings.auth_mode != "local":
        raise HTTPException(
            status_code=501,
            detail="Supabase auth is not wired in this local workspace yet.",
        )
    email = normalize_email(body.email)
    user = session.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(id=str(uuid.uuid4()), email=email, created_at=datetime.now(UTC))
        session.add(user)
        session.commit()
    token = issue_token(
        user.id, settings.local_auth_secret, settings.token_ttl_seconds, email=user.email
    )
    return SessionResponse(token=token, email=user.email, user_id=user.id)


@router.get("/me", response_model=UserResponse)
async def read_me(user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse(email=user.email, user_id=user.id)
