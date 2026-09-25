import secrets
from datetime import UTC, datetime, timedelta
from typing import Literal

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pwdlib import PasswordHash
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from access_docs import access_note
from config import settings
from database import access_db
from models import RevokedToken, Role, User
from schemas import RefreshRequest, TokenResponse, UserAuth, UserSignup

TokenType = Literal["access", "refresh"]
hasher = PasswordHash.recommended()


def not_authorized(message: str = "Invalid Credentials") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=message,
        headers={"WWW-Authenticate": "Bearer"},
    )


def extract_token(token: str, expected_type: TokenType) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_key,
            algorithms=[settings.jwt_algorithm],
            options={"verify_exp": True},
        )
    except jwt.ExpiredSignatureError as e:
        raise not_authorized("Expired token") from e
    except jwt.PyJWTError as e:
        raise not_authorized() from e

    if payload.get("type") != expected_type:
        raise not_authorized()
    return payload


def create_token(client: User, token_type: TokenType) -> str:
    duration = timedelta(
        minutes=(
            settings.access_token_expire_minutes
            if token_type == "access"
            else settings.refresh_token_expire_minutes
        )
    )

    now = datetime.now(UTC)
    data = {
        "sub": str(client.id),
        # "user": client.username,
        "type": token_type,
        "jti": secrets.token_urlsafe(16),
        "iat": now,
        "exp": now + duration,
    }
    return jwt.encode(data, settings.jwt_key, algorithm=settings.jwt_algorithm)


# uh
async def revoke_token(payload: dict, db: AsyncSession) -> bool:
    jti = str(payload["jti"])
    exists = await db.scalar(select(RevokedToken.id).where(RevokedToken.jti == jti))
    if exists:
        return False
    db.add(
        RevokedToken(
            jti=jti,
            user_id=int(payload["sub"]),
            expires_at=datetime.fromtimestamp(payload["exp"], tz=UTC),
        )
    )
    return True


def issue_tokens(client: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_token(client, token_type="access"),
        refresh_token=create_token(client, token_type="refresh"),
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


async def require_auth(token: str = Depends(oauth2_scheme)) -> int:
    payload = extract_token(token, "access")
    return int(payload["sub"])


async def get_current_user(
    user_id: int = Depends(require_auth), db: AsyncSession = Depends(access_db)
) -> User:
    user = await db.get(User, user_id)
    if not user:
        raise not_authorized("Not logged in")
    return user


def require_roles(*roles: Role):
    """Dependency factory: allow only users having one of the given roles.

    The role is read from the DB on each request, so role changes apply
    immediately without waiting for the access token to expire.
    """
    allowed = set(roles)

    async def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    # Read by access_docs to state the allowed roles in the API docs.
    checker.roles = frozenset(allowed)
    return checker


require_curator = require_roles(Role.CURATOR, Role.ADMIN)
require_admin = require_roles(Role.ADMIN)


auth = APIRouter(prefix="/auth")


async def authenticate(username: str, password: str, db: AsyncSession) -> User:
    query = select(User).where(User.username == username)
    user = await db.scalar(query)
    if not user or not hasher.verify(password, user.password):
        raise not_authorized()
    return user


@auth.post("/login", response_model=TokenResponse)
async def login_json(
    data: UserAuth, db: AsyncSession = Depends(access_db)
) -> TokenResponse:
    user = await authenticate(data.username, data.password, db)
    return issue_tokens(user)


@auth.post("/token", response_model=TokenResponse, include_in_schema=False)
async def login_oauth(
    data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(access_db)
) -> TokenResponse:
    user = await authenticate(data.username, data.password, db)
    return issue_tokens(user)


@auth.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@access_note("Новый пользователь получает роль «ученик».")
async def signup(
    data: UserSignup, db: AsyncSession = Depends(access_db)
) -> TokenResponse:
    query = select(User).where(
        or_(User.email == data.email, User.username == data.username)
    )
    user_exists = await db.scalar(query)

    if user_exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or username already taken",
        )
        # if user_exists.email == data.email:
        #    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already taken")
        # if user_exists.login == data.login:
        #    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username is already taken")

    new_user = User(
        username=data.username, email=data.email, password=hasher.hash(data.password)
    )
    try:
        db.add(new_user)
        await db.flush()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or Username already taken",
        ) from e

    return issue_tokens(new_user)


@auth.post("/refresh", response_model=TokenResponse)
@access_note(
    "Нужен действующий refresh-токен в теле запроса; после обмена он отзывается."
)
async def refresh(
    data: RefreshRequest, db: AsyncSession = Depends(access_db)
) -> TokenResponse:
    payload = extract_token(data.refresh_token, "refresh")
    if not (await revoke_token(payload, db)):
        raise not_authorized("Log in again")
    user_id = int(payload["sub"])
    user = await db.get(User, user_id)
    if not user:
        raise not_authorized("User not found")
    return issue_tokens(user)


@auth.post("/logout")
@access_note("Нужен refresh-токен в теле запроса; он отзывается.")
async def logout(data: RefreshRequest, db: AsyncSession = Depends(access_db)):
    payload = extract_token(data.refresh_token, "refresh")
    await revoke_token(payload, db)
    return {"detail": "Logged out"}
