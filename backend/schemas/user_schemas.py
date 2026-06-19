from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, EmailStr, model_validator
from typing import Annotated

UsernameStr = Annotated[str, Field(
    ..., min_length=4, max_length=20, description="用户名"
)]
RawPasswordStr = Annotated[str, Field(
    ..., min_length=6, max_length=20, description="密码"
)]


class RegisterIn(BaseModel):
    email: EmailStr
    username: UsernameStr
    password: RawPasswordStr
    confirm_password: RawPasswordStr
    code: Annotated[str, Field(..., min_length=4, max_length=4)]

    @model_validator(mode="after")
    def password_is_match(self):
        password = self.password
        confirm_password = self.confirm_password
        if password != confirm_password:
            raise ValueError("Password don't match")
        return self


class UserCreateSchema(BaseModel):
    email: EmailStr
    username: UsernameStr
    password: RawPasswordStr


class LoginIn(BaseModel):
    email: EmailStr
    password: RawPasswordStr


class UserSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Annotated[int, Field(...)]
    username: UsernameStr
    email: EmailStr
    role: str
    is_active: bool
    created_at: datetime
    usage_count: int


class LoginOut(BaseModel):
    user: UserSchema
    token: str
