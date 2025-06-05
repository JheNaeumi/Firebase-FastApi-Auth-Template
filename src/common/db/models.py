
from sqlalchemy import Boolean, Column, DateTime, Integer, String

from common.db.schemas import *
from common.db.db import default_base

#TODO Add Display Name and Hashed Password
class User(default_base):
    __tablename__ = 'mUsers'
    __table_args__ = {'schema': 'dbo'}

    id = Column('RecordNo', Integer, primary_key=True)
    uid = Column('UserUID', String(50), unique=True, index=True)
    l_name = Column('LastName', String(225))
    f_name = Column('FirstName', String(225))
    email = Column('EmailAddress', String(225))
    is_email_verified = Column('IsEmailVerified', Boolean, default=False)
    birth_date = Column('BirthDate', DateTime)
    #image uid
    profile_uid = Column('ProfileUid', String(20))
    display_name = Column('DisplayName', String(30))
    hashed_password = Column('HashedPassword', String(255))


    def to_json(self):
        return self.to_schema().model_dump()
    
    def to_schema(self):
        return UserBase(id=self.id,
                        uid=self.uid,
                        lName=self.l_name,
                        fName=self.l_name,
                        email=self.email,
                        emailVerified=self.is_email_verified,
                        birthDate=self.birth_date,
                        profileUid=self.profile_uid)
    
    def to_profile_schema(self):
        return ProfileBase(
            lName=self.l_name,
            fName=self.f_name,
            dname=self.display_name,
            birthDate=self.birth_date,
            email=self.email,
            profileUid=self.profile_uid
        )
    def to_json_profile(self):
        data = self.to_profile_schema().model_dump()
        data['birthDate'] = data['birthDate'].isoformat()
        return data

class Token(default_base):
    __tablename__ = 'tToken'
    __table_args__ = {'schema': 'dbo'}

    id = Column('RecordNo', Integer, primary_key=True)
    uid = Column('UserUID', String(50), unique=True, index=True)
    email = Column('EmailAddress', String(225))
    acess_token = Column('AccessToken', String(255))
    refresh_token = Column('RefreshToken', String(225))

    def to_json(self):
        return self.to_schema().model_dump()
    
    def to_schema(self):
        return TokenBase(
            accessToken=self.acess_token,
            refreshToken=self.refresh_token,
            tokenType='Bearer'
        )

    

