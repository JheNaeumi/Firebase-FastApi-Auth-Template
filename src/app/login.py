

from fastapi.responses import JSONResponse
from typing_extensions import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from common.authentication.authentication import signin_via_firebase, verify_access_token, send_verfication_email
from fastapi.security import OAuth2PasswordRequestForm
from firebase_admin import auth
from common.db import crud, db, schemas
from sqlalchemy.ext.asyncio import AsyncSession
from common.logger import get_logger
from common.cache import redis_helper

logger = get_logger(__name__)
router = APIRouter()

RATE_LIMIT_MAX_ATTEMPTS = 5
RATE_LIMIT_WINDOW = 900  # 15 minutes


async def _authenticate_user(email: str, password: str) -> dict:
    # Check if account is locked due to failed login attempts
    if await redis_helper.is_account_locked(email, RATE_LIMIT_MAX_ATTEMPTS):
        logger.warning(f"Account locked due to failed login attempts: {email}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Account temporarily locked due to too many failed login attempts"
        )

    user = signin_via_firebase(username=email, password=password)
    if not user:
        await redis_helper.increment_failed_login(email, RATE_LIMIT_WINDOW)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email and password"
        )

    try:
        token_claims = auth.verify_id_token(user["idToken"])
        if not token_claims.get("email_verified"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email has not been verified"
            )
    except auth.InvalidIdTokenError as e:
        logger.error(f"Invalid token for user {email}: {e}")
        await redis_helper.increment_failed_login(email, RATE_LIMIT_WINDOW)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

    # Reset failed login count on successful authentication
    await redis_helper.reset_failed_login(email)
    return user


@router.post("/login")
async def login(
    cred: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: AsyncSession = Depends(db.get_default_db)
):
    email = cred.username
    password = cred.password

    # Check rate limit
    if not await redis_helper.check_rate_limit(email, RATE_LIMIT_MAX_ATTEMPTS, RATE_LIMIT_WINDOW):
        logger.warning(f"Login rate limit exceeded for {email}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later."
        )

    try:
        user = await _authenticate_user(email, password)
        await crud.update_email_as_verfied(db, email=email)

        created_token = await crud.create_token(
            db=db,
            token=schemas.TokenCreate(
                uid=user["localId"],
                email=user["email"],
                accessToken=user["idToken"],
                refreshToken=user["refreshToken"]
            )
        )

        if created_token:
            user_info = await crud.get_user_by_email(db=db, email=email)

            # Set session timeout: 15 min inactivity, 8 hours absolute max
            await redis_helper.set_session(
                user_info.uid,
                inactivity_ttl=900,  # 15 minutes
                absolute_ttl=28800   # 8 hours
            )

            await redis_helper.set_user_online(user_info.uid)
            logger.info(f"User {email} logged in successfully")
            return JSONResponse(
                content={
                    "message": "Successfully logged in",
                    "user": user_info.to_json_profile(),
                    "token": created_token.to_json()
                },
                status_code=status.HTTP_200_OK
            )

        logger.error(f"Failed to create token for user {email}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create session token"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error for {email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during login"
        )


@router.post("/token")
async def get_tokens(cred: Annotated[OAuth2PasswordRequestForm, Depends()]):
    email = cred.username
    password = cred.password

    # Check rate limit
    if not await redis_helper.check_rate_limit(email, RATE_LIMIT_MAX_ATTEMPTS, RATE_LIMIT_WINDOW):
        logger.warning(f"Token rate limit exceeded for {email}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Please try again later."
        )

    try:
        user = await _authenticate_user(email, password)
        logger.info(f"Tokens issued for user {email}")
        return {
            "access_token": user["idToken"],
            "refresh_token": user["refreshToken"],
            "token_type": "bearer"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token generation error for {email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate tokens"
        )


@router.delete("/token")
async def revoke_tokens(token: Annotated[str, Depends(verify_access_token)] = None, user_uid: str = Depends(verify_access_token)):
    # Note: token is extracted from the dependency, user_uid is the return value
    try:
        # Get the token from the request header for blacklisting
        auth_header = None

        auth.revoke_refresh_tokens(user_uid)
        await redis_helper.invalidate_user_tokens(user_uid)
        await redis_helper.clear_session(user_uid)
        await redis_helper.set_user_offline(user_uid)

        logger.info(f"Tokens revoked for user {user_uid}")
        return {"status": "revoked", "message": "All tokens have been revoked"}
    except Exception as e:
        logger.error(f"Failed to revoke tokens for user {user_uid}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke tokens"
        )
