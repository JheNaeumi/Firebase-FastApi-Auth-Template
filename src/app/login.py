

from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing_extensions import Annotated
from fastapi import APIRouter, Depends, Form, HTTPException, status
from common.authentication.authentication import *
from fastapi.security import OAuth2PasswordRequestForm
from firebase_admin import auth
from common.db import crud, db, schemas
from sqlalchemy.ext.asyncio import AsyncSession


router = APIRouter()


@router.post("/login")
async def login(cred: Annotated[OAuth2PasswordRequestForm, Depends()],
                db: AsyncSession = Depends(db.get_default_db)):

    # Get Username and Password
    email = cred.username
    password = cred.password

    # LogIn
    user = signin_via_firebase(username=email, password=password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid Email and Password')

    # Check email if verified
    if not auth.verify_id_token(user['idToken'])['email_verified']:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail='Email has not been verified')

    # Update DB email verified
    await crud.update_email_as_verfied(db, email=email)

    

    # Create Token Model and Store/Create in DB
    created_token = await crud.create_token(db=db, token=schemas.TokenCreate(
        uid=user['localId'],
        email=user['email'],
        accessToken=user['idToken'],
        refreshToken=user['refreshToken']
    ))
    # Get User Info
    user = await crud.get_user_by_email(db=db, email=email)

    
    # Pass Access and Refresh Token
    if created_token:
        return JSONResponse(
            content={"message": "Succesfully Logged In",
                     "user": user.to_json_profile(),
                     "token" : created_token.to_json()
                   },
            status_code=status.HTTP_200_OK
        )
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST
    )

@router.post("/token")
async def token(cred: Annotated[OAuth2PasswordRequestForm, Depends()],):

    # Get Username and Password
    email = cred.username
    password = cred.password

    # LogIn
    user = signin_via_firebase(username=email, password=password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid Email and Password')

    # Check email if verified
    if not auth.verify_id_token(user['idToken'])['email_verified']:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail='Email has not been verified')
    print(user)
    return {"access_token" : user['idToken'], "refresh_token": user['refreshToken'], "token_type" : "bearer"}

# @router.get("/signout")
# async def sign_out():

#     response = ''

#     if response:
#         return response
#     raise HTTPException(
#         status_code=status.HTTP_400_BAD_REQUEST
#     )
