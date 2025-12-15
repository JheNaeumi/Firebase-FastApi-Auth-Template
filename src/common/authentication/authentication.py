from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing_extensions import Annotated
from configurations.firebase import *
from firebase_admin import auth

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/2025/token")

def signin_via_firebase(username: str, password: str):
    try:
        user = pb.auth().sign_in_with_email_and_password(
            email=username, password=password)
        

        if user is None:
            return None

        return user
    except Exception as e:
        print(e)


def create_user_firebase(username: str, password: str):
    try:
        created_user = pb.auth().create_user_with_email_and_password(
            email=username, password=password)

        if created_user is None:
            return None

        return created_user

    except Exception as e:
        print(e)


def send_verfication_email(tokenId: str):
    try:
        verification_result = pb.auth().send_email_verification(tokenId)

        if verification_result is None:
            return None

        return verification_result
    except Exception as e:
        print(e)


def verify_access_token(token: Annotated[str, Depends(oauth2_scheme)]):
    try:
        decoded_token = auth.verify_id_token(token, check_revoked=True)
        uid = decoded_token['uid']

        return uid

    except (auth.ExpiredIdTokenError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Could not validate credentials',
            headers={"WWW-Authenticate": token}
        )
    except Exception as e:
        print(e)


