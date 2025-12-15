from fastapi import APIRouter, Depends

from common.authentication.authentication import verify_access_token
from sqlalchemy.ext.asyncio import AsyncSession
from common.db import db, crud

router = APIRouter()


@router.get("/home")
async def home(userUID=Depends(verify_access_token), db: AsyncSession = Depends(db.async_get_default_db)):

    
    user = await crud.get_user_uid(db=db, uid=userUID)
    return {f"Hello, {user.f_name}" }


