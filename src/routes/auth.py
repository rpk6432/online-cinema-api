from fastapi import APIRouter, Request
from kombu.exceptions import OperationalError
from loguru import logger

from core.config import settings
from core.dependencies import ActiveUser, CurrentUser, DBSession
from core.exceptions import (
    AlreadyExistsError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
)
from core.rate_limit import limiter
from core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from crud.token import (
    create_activation_token,
    create_password_reset_token,
    create_refresh_token_record,
    delete_activation_token,
    delete_password_reset_token,
    delete_refresh_token,
    get_activation_token,
    get_password_reset_token,
    get_refresh_token,
)
from crud.user import user_crud
from schemas.auth import (
    ActivateRequest,
    LoginRequest,
    PasswordChangeRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    RefreshRequest,
    RegisterRequest,
    ResendActivationRequest,
    TokenResponse,
)
from schemas.common import MessageResponse
from schemas.users import UserResponse
from tasks.email import send_activation_email, send_password_reset_email

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    status_code=201,
    summary="Register a new user",
    responses={409: {"description": "Email already registered"}},
)
@limiter.limit(settings.rate_limit)
async def register(
    request: Request, body: RegisterRequest, db: DBSession
) -> MessageResponse:
    """Create a new user account and send an activation email."""
    existing = await user_crud.get_by_email(db, body.email)
    if existing:
        raise AlreadyExistsError("Email already registered")

    hashed = hash_password(body.password)
    user = await user_crud.create_user(db, body.email, hashed)

    token = await create_activation_token(db, user.id)
    try:
        send_activation_email.delay(user.email, token.token)
    except OperationalError:
        logger.warning("Failed to queue activation email for {}", user.email)

    return MessageResponse(detail="Check your email to activate your account")


@router.post(
    "/activate",
    summary="Activate user account",
    responses={404: {"description": "Invalid or expired token"}},
)
async def activate(body: ActivateRequest, db: DBSession) -> MessageResponse:
    """Activate a user account using a one-time activation token."""
    token = await get_activation_token(db, body.token)
    if token is None:
        raise NotFoundError("Invalid or expired activation token")

    user = await user_crud.get(db, token.user_id)
    if user is None:
        raise NotFoundError("User not found")

    await user_crud.update(db, user, is_active=True)
    await delete_activation_token(db, token)

    return MessageResponse(detail="Account activated successfully")


@router.post(
    "/resend-activation",
    summary="Resend activation email",
)
@limiter.limit(settings.rate_limit)
async def resend_activation(
    request: Request, body: ResendActivationRequest, db: DBSession
) -> MessageResponse:
    """Resend activation email if the account exists and is not yet active."""
    user = await user_crud.get_by_email(db, body.email)
    if user is not None and not user.is_active:
        token = await create_activation_token(db, user.id)
        try:
            send_activation_email.delay(user.email, token.token)
        except OperationalError:
            logger.warning("Failed to queue activation email for {}", user.email)

    return MessageResponse(
        detail="If this email is registered, an activation link was sent"
    )


@router.post(
    "/login",
    summary="Log in",
    responses={
        401: {"description": "Invalid credentials"},
        403: {"description": "Account is not activated"},
    },
)
@limiter.limit(settings.rate_limit)
async def login(request: Request, body: LoginRequest, db: DBSession) -> TokenResponse:
    """Authenticate with email and password, receive a JWT token pair."""
    user = await user_crud.get_by_email(db, body.email)
    if user is None or not verify_password(body.password, user.hashed_password):
        raise UnauthorizedError("Invalid email or password")
    if not user.is_active:
        raise ForbiddenError("Account is not activated")

    access = create_access_token(user.id)
    refresh_jwt = create_refresh_token(user.id)

    await create_refresh_token_record(db, user.id, refresh_jwt)

    return TokenResponse(access_token=access, refresh_token=refresh_jwt)


@router.post(
    "/logout",
    summary="Log out",
    responses={401: {"description": "Not authenticated"}},
)
async def logout(
    body: RefreshRequest, _user: CurrentUser, db: DBSession
) -> MessageResponse:
    """Invalidate a refresh token, ending the session."""
    await delete_refresh_token(db, body.refresh_token)
    return MessageResponse(detail="Logged out successfully")


@router.post(
    "/refresh",
    summary="Refresh token pair",
    responses={401: {"description": "Invalid or expired refresh token"}},
)
async def refresh(body: RefreshRequest, db: DBSession) -> TokenResponse:
    """Exchange a valid refresh token for a new JWT token pair."""
    token_record = await get_refresh_token(db, body.refresh_token)
    if token_record is None:
        raise UnauthorizedError("Invalid or expired refresh token")

    await delete_refresh_token(db, body.refresh_token)

    access = create_access_token(token_record.user_id)
    new_refresh = create_refresh_token(token_record.user_id)

    await create_refresh_token_record(db, token_record.user_id, new_refresh)

    return TokenResponse(access_token=access, refresh_token=new_refresh)


@router.post(
    "/password-change",
    summary="Change password",
    responses={401: {"description": "Current password is incorrect"}},
)
async def password_change(
    body: PasswordChangeRequest, user: ActiveUser, db: DBSession
) -> MessageResponse:
    """Change the password of the currently authenticated user."""
    if not verify_password(body.old_password, user.hashed_password):
        raise UnauthorizedError("Current password is incorrect")

    hashed = hash_password(body.new_password)
    await user_crud.update(db, user, hashed_password=hashed)

    return MessageResponse(detail="Password changed successfully")


@router.post(
    "/password-reset",
    summary="Request password reset",
)
@limiter.limit(settings.rate_limit)
async def password_reset(
    request: Request, body: PasswordResetRequest, db: DBSession
) -> MessageResponse:
    """Send a password reset email if the account exists."""
    user = await user_crud.get_by_email(db, body.email)
    if user is not None:
        token = await create_password_reset_token(db, user.id)
        try:
            send_password_reset_email.delay(user.email, token.token)
        except OperationalError:
            logger.warning("Failed to queue password reset email for {}", user.email)

    return MessageResponse(
        detail="If this email is registered, reset instructions were sent"
    )


@router.post(
    "/password-reset/confirm",
    summary="Confirm password reset",
    responses={404: {"description": "Invalid or expired token"}},
)
async def password_reset_confirm(
    body: PasswordResetConfirmRequest, db: DBSession
) -> MessageResponse:
    """Reset the password using a valid reset token."""
    token = await get_password_reset_token(db, body.token)
    if token is None:
        raise NotFoundError("Invalid or expired reset token")

    user = await user_crud.get(db, token.user_id)
    if user is None:
        raise NotFoundError("User not found")

    hashed = hash_password(body.new_password)
    await user_crud.update(db, user, hashed_password=hashed)
    await delete_password_reset_token(db, token)

    return MessageResponse(detail="Password reset successfully")


@router.get(
    "/me",
    summary="Get current user",
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Account is not activated"},
    },
)
async def me(user: ActiveUser) -> UserResponse:
    """Return the profile of the currently authenticated user."""
    return UserResponse.model_validate(user)
