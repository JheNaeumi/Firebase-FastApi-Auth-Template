

from fastapi import APIRouter, Depends, Form, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
import logging
from common.db import db, crud, schemas
from common.authentication.authentication import *
from firebase_admin import auth
import bcrypt
router = APIRouter()

logger = logging.getLogger(__name__)
# Get Profile
@router.get('/profile')
async def get_profile(userUID=Depends(verify_access_token), db: AsyncSession = Depends(db.async_get_default_db)):
    # Get User
    user = await crud.get_user_uid(db=db, uid=userUID)

    if not user:
        return None

    user_profile = user.to_profile_schema().model_dump()

    if user_profile:
        return user_profile
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

# Update Profile
@router.put('/profile')
async def update_profile(fname:  Annotated[str, Form()], lname:  Annotated[str, Form()],
                         dname: Annotated[str, Form()], userUID=Depends(verify_access_token), db: AsyncSession = Depends(db.async_get_default_db)):

    try:
        # Update firebase user
        auth.update_user(
            uid=userUID,
            display_name=dname,
        )
        # Update local user
        updated_user = await crud.update_user(
            db=db,
            uid=userUID,
            fname=fname,
            lname=lname,
            dname=dname
        )
        return updated_user.to_profile_schema()
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Something went wrong.')

# Update password
@router.put('/profile/password')
async def update_password(currentpassword: Annotated[str, Form()], newpassword: Annotated[str, Form()], userUID=Depends(verify_access_token), db: AsyncSession = Depends(db.async_get_default_db)):

    # Check current password
    user = await crud.get_user_uid(db=db, uid=userUID)
    hashed_current_password = user.hashed_password

    if bcrypt.checkpw(currentpassword.encode("utf-8"), hashed_current_password.encode("utf-8")):
        try:
            # Update local password
            new_hashed_password = bcrypt.hashpw(
                newpassword.encode("utf-8"), salt=bcrypt.gensalt())
            await crud.update_existing_password(
                db=db, newhashedpassword=new_hashed_password.decode("utf-8"), uid=userUID)

            # Update firebase password
            auth.update_user(
                uid=userUID,
                password=newpassword
            )
            return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "Password Updated"})
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e)
        
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Password does not Match.')
