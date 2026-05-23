

from fastapi.responses import JSONResponse
from typing_extensions import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from common.authentication.authentication import signin_via_firebase, verify_access_token, send_verfication_email
from fastapi.security import OAuth2PasswordRequestForm
from firebase_admin import auth
from common.db import crud, db, schemas
from sqlalchemy.ext.asyncio import AsyncSession
from common.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


async def _authenticate_user(email: str, password: str) -> dict:
    user = signin_via_firebase(username=email, password=password)
    if not user:
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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

    return user


@router.post("/login")
async def login(
    cred: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: AsyncSession = Depends(db.get_default_db)
):
    email = cred.username
    password = cred.password

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
async def revoke_tokens(user_uid: str = Depends(verify_access_token)):
    try:
        auth.revoke_refresh_tokens(user_uid)
        logger.info(f"Tokens revoked for user {user_uid}")
        return {"status": "revoked", "message": "All tokens have been revoked"}
    except Exception as e:
        logger.error(f"Failed to revoke tokens for user {user_uid}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke tokens"
        )
