import hashlib
import smtplib
import secrets
from datetime import datetime, timedelta
from email.message import EmailMessage
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.config import get_settings
from app.dependencies import DbSession, get_current_user
from app.models import PasswordResetToken, User
from app.schemas import PasswordResetConfirm, PasswordResetRequest, TokenOut, UserOut, UserRegister
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: DbSession):
    user = User(name=payload.name.strip(), email=str(payload.email).lower(), phone=payload.phone,
                password_hash=hash_password(payload.password), role="customer")
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email is already registered")
    db.refresh(user)
    return user

@router.post("/login", response_model=TokenOut)
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession):
    user = db.scalar(select(User).where(User.email == form.username.lower()))
    if not user or not user.is_active or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password",
                            headers={"WWW-Authenticate": "Bearer"})
    return TokenOut(access_token=create_access_token(str(user.id), user.role))

@router.get("/me", response_model=UserOut)
def me(user: Annotated[User, Depends(get_current_user)]):
    return user



def _send_password_reset_email(email: str, token: str) -> None:
    reset_url = f"{settings.frontend_reset_url}?token={token}"
    message = EmailMessage()
    message["Subject"] = "Reset your CineBook password"
    message["From"] = settings.smtp_from_email or settings.smtp_username
    message["To"] = email
    message.set_content(
        "A password reset was requested for your CineBook account. "
        "Open this link within 30 minutes to choose a new password:\\n\\n"
        f"{reset_url}\\n\\n"
        "If you did not request this, you can ignore this message."
    )
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=12) as client:
        if settings.smtp_use_tls:
            client.starttls()
        if settings.smtp_username:
            client.login(settings.smtp_username, settings.smtp_password)
        client.send_message(message)


@router.post("/password-reset/request")
def request_password_reset(payload: PasswordResetRequest, db: DbSession):
    # Always use the same outward message to avoid account enumeration.
    generic = {"message": "If an account exists for that address, password reset instructions have been sent."}
    user = db.scalar(select(User).where(User.email == str(payload.email).lower(), User.is_active.is_(True)))
    if not user:
        return generic

    raw_token = secrets.token_urlsafe(36)
    digest = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    db.add(PasswordResetToken(
        user_id=user.id,
        token_hash=digest,
        expires_at=datetime.now() + timedelta(minutes=30),
    ))
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=503, detail="Could not create a password reset request")

    if settings.smtp_host and settings.smtp_from_email:
        try:
            _send_password_reset_email(user.email, raw_token)
        except Exception:
            raise HTTPException(status_code=503, detail="Password reset email could not be delivered. Check SMTP configuration.")
    elif settings.app_env.lower() not in {"production", "prod"}:
        # Local development convenience only. Never expose reset tokens in production.
        return {**generic, "development_token": raw_token, "expires_in_minutes": 30}

    return generic


@router.post("/password-reset/confirm")
def confirm_password_reset(payload: PasswordResetConfirm, db: DbSession):
    digest = hashlib.sha256(payload.token.encode("utf-8")).hexdigest()
    item = db.scalar(select(PasswordResetToken).where(
        PasswordResetToken.token_hash == digest,
        PasswordResetToken.used_at.is_(None),
        PasswordResetToken.expires_at > datetime.now(),
    ).with_for_update())
    if not item:
        raise HTTPException(status_code=400, detail="Reset token is invalid or expired")
    user = db.get(User, item.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=400, detail="Reset token is invalid or expired")
    user.password_hash = hash_password(payload.new_password)
    item.used_at = datetime.now()
    db.execute(
        PasswordResetToken.__table__.update()
        .where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.id != item.id,
            PasswordResetToken.used_at.is_(None),
        )
        .values(used_at=datetime.now())
    )
    db.commit()
    return {"message": "Password updated. You can now sign in with your new password."}
