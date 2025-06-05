from sqlalchemy.orm import Session

from common.db import models, schemas


#Optimize db Session
def create_new_user(db: Session, user: schemas.UserCreate):

    new_user = models.User(
        uid=user.uid,
        email=user.email,
        l_name=user.lName.upper(),
        f_name=user.fName.upper(),
        display_name=user.dName,
        hashed_password=user.hpassword,
        is_email_verified=user.emailVerified,
        birth_date=user.birthDate,
        profile_uid=user.profileUid
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

def update_user(db: Session, uid: str, fname:str, lname:str, dname:str):
    db.query(models.User).filter(models.User.uid == uid).update({
        "l_name": lname,
        "f_name": fname,
        "display_name": dname,
    })
    db.commit()
    #return updated user
    return get_user_uid(db=db, uid=uid)

def update_existing_password(db: Session, uid: str, newhashedpassword : str):
    db.query(models.User).filter(models.User.uid == uid).update({
        "hashed_password": newhashedpassword,
    })
    db.commit()

def get_user_by_email(db:Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def get_user_uid(db:Session, uid: str):
    return db.query(models.User).filter(models.User.uid == uid).first()


def update_email_as_verfied(db: Session, email: str):
    #Check if already verified
    user = db.query(models.User).filter(models.User.email == email).first()
    if user.is_email_verified == False:
        db.query(models.User).filter(models.User.email == email).update({
            "is_email_verified": True
        })
        db.commit()
    
def create_token(db: Session, token: schemas.TokenCreate):

    new_token = models.Token(
        uid=token.uid,
        email=token.email,
        acess_token=token.accessToken,
        refresh_token=token.refreshToken,
    )
    db.add(new_token)
    db.commit()
    db.refresh(new_token)
    return new_token
