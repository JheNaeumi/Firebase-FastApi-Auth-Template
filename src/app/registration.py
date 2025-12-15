
from datetime import datetime
from typing import Union
import uuid
from fastapi.responses import JSONResponse
from typing_extensions import Annotated
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from firebase_admin import auth
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from common.db import crud, db, schemas
from common.helpers.file_system_helper import dir_path_profile, save_image, validate_email, validate_password
from common.authentication.authentication import *
import bcrypt
router = APIRouter()

# Create New User
@router.post("/register")
async def register_new_user(email: Annotated[str, Form(media_type="multipart/form-data")], password:  Annotated[str, Form(media_type="multipart/form-data")],
                            fname:  Annotated[str, Form(media_type="multipart/form-data")], lname:  Annotated[str, Form(media_type="multipart/form-data")],
                            dname: Annotated[str, Form(media_type="multipart/form-data")],
                            birthdate:  Annotated[datetime, Form(media_type="multipart/form-data")], profileImage: Annotated[UploadFile, File()] = None,
                            db: AsyncSession = Depends(db.get_default_db)):
    try:
        # Validate Email and Password
        valid_email = validate_email(email=email)
        valid_password = validate_password(password=password)

        if not valid_email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Email is not Valid')
        
        if not valid_password:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Password is not Valid')
        
    
        # Check if email is registered return "Already Registered"
        email_exist = auth.get_user_by_email(email=email)
        if email_exist:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Email Already Exist'
            )
    except auth.UserNotFoundError as e:
        pass

    # Create Account in Firebase
    created_user = create_user_firebase(username=email, password=password)

    # Get UID from created user
    uid = ''
    uid = created_user['localId']

    # Hash Password
    hashed_password = bcrypt.hashpw(
        password=password.encode("utf-8"), salt=bcrypt.gensalt())  # Default gensalt

    # Store Image and Create profile directory
    directory = dir_path_profile()
    profile_uid = ''
    if profileImage is not None:
        profile_uid = uuid.uuid4().hex
        await save_image(file=profileImage, file_name=profile_uid, directory=directory)
    
    # Save/Create Account in DB
    db_created_user = await crud.create_new_user(db=db, user=schemas.UserCreate(
        uid=uid,
        lName=lname,
        fName=fname,
        dName=dname,
        hpassword=hashed_password.decode("utf-8"),
        email=email,
        birthDate=birthdate,
        profileUid=profile_uid
    ))

    # Generate Email For Verification
    try:
        send_verfication_email(created_user["idToken"])
    except Exception as e:
        print(e)
        pass

    # Return Success
    if db_created_user:
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "message": "User successfully created. Kindly verify email sent."}
        )
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Something went wrong.')

