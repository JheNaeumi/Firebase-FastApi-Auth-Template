


from datetime import date, datetime
from typing import Any, Union

from fastapi import Form
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

# Registration - I
class RegistrationRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=8, max_length=128, description="User password")
    fname: str = Field(..., min_length=2, max_length=50, description="First name")
    lname: str = Field(..., min_length=2, max_length=50, description="Last name")
    dname: str = Field(..., min_length=3, max_length=50, description="Display name")
    birthdate: datetime = Field(..., description="Birth date")


    @classmethod
    def as_form(cls, 
        email: str = Form(...),
        password: str = Form(...),
        fname: str = Form(...),
        lname: str = Form(...),
        dname: str = Form(...),
        birthdate: datetime = Form(...)
    ):
        return cls(email=email, password=password, fname=fname, lname=lname, dname=dname, birthdate=birthdate)
    @field_validator('email')
    @classmethod
    def validate_email_format(cls, value: str) -> str:
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', value):
            raise ValueError('Invalid email format')
        return value.lower()

    @field_validator('fname', 'lname', 'dname')
    @classmethod
    def validate_names(cls, value: str) -> str:
        if not re.match(r"^[a-zA-Z\s\-'\.]+$", value):
            raise ValueError('Name contains invalid characters')
        return value.strip()

    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if not any(c.isupper() for c in value):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in value):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in value):
            raise ValueError('Password must contain at least one number')
        return value

    @field_validator('birthdate')
    @classmethod
    def validate_age(cls, value: datetime) -> datetime:
        today = datetime.today()
        age = today.year - value.year
        if age < 13:
            raise ValueError('Must be at least 13 years old')
        if age > 120:
            raise ValueError('Invalid birth date')
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
