


from datetime import date, datetime
from typing import Any, Union

from pydantic import BaseModel, Field, field_validator
import re

# Response - [O/Out]
# Request - [I/In]

# Response - O
class ResponseBase(BaseModel):
    data: Union[Any, None] = None,
    code: int
    succeed: bool
    finished: Union[bool, None] = True
    error: Union[str, None] = ""
    count: int = 0

# User 
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


# Profile 
class ProfileBase(BaseModel):
    lName : str
    fName : str
    email : str
    dname : str
    birthDate : datetime
    profileUid: Union[str, str] = ""

# Profile - I
class UpdateProfile(BaseModel):
    fname: str = Field(..., min_length=2, max_length=50)
    lname: str = Field(..., min_length=2, max_length=50)
    dname: str = Field(..., min_length=3, max_length=50)

# Password - I 
class UpdatePassword(BaseModel):
    current_password: str = Field(..., min_length=8)
    new_password: str = Field(..., min_length=8, max_length=128)
    
    @field_validator('new_password')
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if not any(c.isupper() for c in value):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in value):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in value):
            raise ValueError('Password must contain at least one number')
        return value

# Token
class TokenCreate(BaseModel):
    uid : str
    email :str
    accessToken : str
    refreshToken : str

class TokenBase(BaseModel):
    accessToken : str
    refreshToken : str
    tokenType : str
