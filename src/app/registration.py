
from datetime import datetime
from typing import Union
import uuid
from fastapi.responses import JSONResponse
from typing_extensions import Annotated
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from firebase_admin import auth
from sqlalchemy.ext.asyncio import AsyncSession
from common.db import crud, db, schemas
from common.helpers.file_system_helper import dir_path_profile, save_image
from common.authentication.authentication import create_user_firebase, send_verfication_email
from common.logger import get_logger
import bcrypt

logger = get_logger(__name__)
router = APIRouter()


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_new_user(
    registration: schemas.RegistrationRequest,
    profile_image: UploadFile | None = File(None),
    db: AsyncSession = Depends(db.get_default_db)
):
    try:
        # Check if email already exists in Firebase
        try:
            auth.get_user_by_email(email=registration.email)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        except auth.UserNotFoundError:
            pass

        # Create Firebase user
        created_user = create_user_firebase(
            username=registration.email,
            password=registration.password
        )
        user_uid = created_user["localId"]

        # Hash password for database
        hashed_password = bcrypt.hashpw(
            registration.password.encode("utf-8"),
            bcrypt.gensalt()
        )

        # Handle profile image
        profile_uid = ""
        if profile_image is not None:
            profile_uid = uuid.uuid4().hex
            directory = dir_path_profile()
            await save_image(
                file=profile_image,
                file_name=profile_uid,
                directory=directory
            )

        # Create user in database
        db_created_user = await crud.create_new_user(
            db=db,
            user=schemas.UserCreate(
                uid=user_uid,
                lName=registration.lname,
                fName=registration.fname,
                dName=registration.dname,
                hpassword=hashed_password.decode("utf-8"),
                email=registration.email,
                birthDate=registration.birthdate,
                profileUid=profile_uid
            )
        )

        if not db_created_user:
            logger.error(f"Failed to create user record in database for {registration.email}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user account"
            )

        # Send verification email
        try:
            send_verfication_email(created_user["idToken"])
            logger.info(f"Verification email sent to {registration.email}")
        except Exception as e:
            logger.warning(f"Failed to send verification email to {registration.email}: {str(e)}")

        logger.info(f"User {registration.email} successfully registered")
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "message": "User successfully created. Please verify your email."
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error for {registration.email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during registration"
        )

