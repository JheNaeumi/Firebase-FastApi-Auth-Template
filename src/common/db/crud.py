from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from common.db import models, schemas
from sqlalchemy import update, func, select, delete

#Optimize db Session
async def create_new_user(db: AsyncSession, user: schemas.UserCreate):

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
    await db.commit()
    await db.refresh(new_user)
    return new_user

async def update_user(db: AsyncSession, uid: str, fname:str, lname:str, dname:str):
    # db.query(models.User).filter(models.User.uid == uid).update({
    #     "l_name": lname,
    #     "f_name": fname,
    #     "display_name": dname,
    # })
    await db.execute(update(models.User).where(models.User.uid == uid).values(l_name=lname, f_name=fname, display_name=dname))
    await db.commit()
    #return updated user
    return await get_user_uid(db=db, uid=uid)

async def update_existing_password(db: AsyncSession, uid: str, newhashedpassword : str):
    # db.query(models.User).filter(models.User.uid == uid).update({
    #     "hashed_password": newhashedpassword,
    # })
    await db.execute(update(models.User).where(models.User.uid == uid).values(hashed_password = newhashedpassword))
    await db.commit()

async def get_user_by_email(db:AsyncSession, email: str):
    #return db.query(models.User).filter(models.User.email == email).first()
    return (await db.execute(select(models.User).where(models.User.email == email))).scalar_one()

async def get_user_uid(db:AsyncSession, uid: str):
    #return db.query(models.User).filter(models.User.uid == uid).first()
    return (await db.execute(select(models.User).where(models.User.uid == uid))).scalar_one()

async def update_email_as_verfied(db: AsyncSession, email: str):
    #Check if already verified
    #user = db.query(models.User).filter(models.User.email == email).first()
    user:models.User = (await db.execute(select(models.User).where(models.User.email == email))).scalar_one()
    if user.is_email_verified == False:
        # db.query(models.User).filter(models.User.email == email).update({
        #     "is_email_verified": True
        # })
        await db.execute(update(models.User).where(models.User.email == email).values(is_email_verified=True))
        await db.commit()
    
async def create_token(db: AsyncSession, token: schemas.TokenCreate):

    new_token = models.Token(
        uid=token.uid,
        email=token.email,
        acess_token=token.accessToken,
        refresh_token=token.refreshToken,
    )
    db.add(new_token)
    await db.commit()
    await db.refresh(new_token)
    return new_token
