


from datetime import date, datetime
from typing import Any, Union

from pydantic import BaseModel, Field, field_validator
import re

class ResponseBase(BaseModel):
    data: Union[Any, None] = None,
    code: int
    succeed: bool
    finished: Union[bool, None] = True
    error: Union[str, None] = ""
    count: int = 0


class UserBase(BaseModel):
    id: int
    uid: str
    lName: str
    fName: str
    email: str
    dName: str
    hashedPassword : str
    emailVerified: Union[bool, None] = False
    birthDate: datetime
    profileUid: Union[str, str] = ""

class UserCreate(BaseModel):
    uid: str
    lName: str = Field(..., min_length=2, max_length=50)
    fName: str = Field(..., min_length=2, max_length=50)
    email: str
    hpassword : str = Field(..., min_length=8, max_length=128)
    dName : str = Field(..., min_length=3, max_length=50)
    emailVerified: Union[bool, None] = False
    birthDate: datetime
    profileUid: Union[str, str] = ""

    #validate names
    @field_validator('lName', 'fName', 'dName')
    @classmethod
    def validate_names(cls, value: str) -> str:
        if not re.match(r"^[a-zA-Z\s\-'\.]+$", value):
            raise ValueError('Name contains invalid characters')
        return value.strip()
    #validate age
    @field_validator('birthDate')
    @classmethod
    def validate_age(cls, value ):
        today = datetime.today()
        age = today.year - value.year
        if age < 13:
            raise ValueError('Must be at least 13 years old')
        if age > 120:
            raise ValueError('Invalid birth date')
        return value



class ProfileBase(BaseModel):
    lName : str
    fName : str
    email : str
    dname : str
    birthDate : datetime
    profileUid: Union[str, str] = ""

class TokenCreate(BaseModel):
    uid : str
    email :str
    accessToken : str
    refreshToken : str

class TokenBase(BaseModel):
    accessToken : str
    refreshToken : str
    tokenType : str
