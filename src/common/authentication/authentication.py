from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing_extensions import Annotated
from configurations.firebase import *
from firebase_admin import auth
from common.cache import redis_helper
from common.logger import get_logger

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/2025/token")
logger = get_logger(__name__)

def signin_via_firebase(username: str, password: str):
    try:
        user = pb.auth().sign_in_with_email_and_password(
            email=username, password=password)

        if user is None:
            return None

        return user
    except Exception as e:
        logger.error(f"Firebase sign-in error: {str(e)}")
        return None


def create_user_firebase(username: str, password: str):
    try:
        created_user = pb.auth().create_user_with_email_and_password(
            email=username, password=password)

        if created_user is None:
            return None

        return created_user
    except Exception as e:
        logger.error(f"Firebase user creation error: {str(e)}")
        return None


def send_verfication_email(tokenId: str):
    try:
        verification_result = pb.auth().send_email_verification(tokenId)

        if verification_result is None:
            return None

        return verification_result
    except Exception as e:
        logger.error(f"Email verification send error: {str(e)}")
        return None


async def verify_access_token(token: Annotated[str, Depends(oauth2_scheme)]):
    try:
        # Check if token is blacklisted
        if await redis_helper.is_token_blacklisted(token):
            logger.warning("Access attempt with blacklisted token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked"
            )

        # Try to get cached token claims
        decoded_token = await redis_helper.get_cached_token(None, token)

        if decoded_token:
            user_uid = decoded_token.get("uid")

            # Check if session is still active (inactivity timeout)
            is_active, reason = await redis_helper.is_session_active(user_uid)
            if not is_active:
                logger.warning(f"Session expired for user {user_uid}: {reason}")
                if reason == "inactivity_timeout":
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Session expired due to inactivity. Please login again."
                    )
                elif reason == "absolute_timeout":
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Session expired. Please login again."
                    )

            # Refresh inactivity timeout (reset the 15-minute timer)
            await redis_helper.refresh_session(user_uid)
            logger.debug("Token verified from cache, session refreshed")
            return user_uid

        # If not cached, verify with Firebase
        decoded_token = auth.verify_id_token(token, check_revoked=True)
        uid = decoded_token.get("uid")

        # Check if session is still active (inactivity timeout)
        is_active, reason = await redis_helper.is_session_active(uid)
        if not is_active:
            logger.warning(f"Session expired for user {uid}: {reason}")
            if reason == "inactivity_timeout":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Session expired due to inactivity. Please login again."
                )
            elif reason == "absolute_timeout":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Session expired. Please login again."
                )

        # Refresh inactivity timeout
        await redis_helper.refresh_session(uid)

        # Cache the token claims for future requests
        await redis_helper.cache_token(uid, token, decoded_token)
        logger.debug(f"Token verified and cached for user {uid}, session refreshed")

        return uid

    except HTTPException:
        raise
    except auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except auth.RevokedIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked"
        )
    except Exception as e:
        logger.error(f"Token verification error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )


