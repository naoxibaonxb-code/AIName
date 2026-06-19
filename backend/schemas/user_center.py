from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from schemas.user_schemas import UserSchema


class UserCenterOut(BaseModel):
    user: UserSchema
    last_login_at: datetime | None = None
    login_count: int = 0


class ProfileUpdateIn(BaseModel):
    username: str | None = Field(None, min_length=4, max_length=20)
    email: EmailStr | None = None
    email_code: str | None = Field(None, min_length=4, max_length=4)
    current_password: str | None = Field(None, min_length=6, max_length=20)

    @field_validator("username")
    @classmethod
    def username_not_blank(cls, value: str | None):
        if value is None:
            return value
        value = value.strip()
        if len(value) < 4:
            raise ValueError("用户名至少需要 4 个非空字符")
        return value

    @model_validator(mode="after")
    def at_least_one_field(self):
        if self.username is None and self.email is None:
            raise ValueError("至少需要修改一项资料")
        return self


class PasswordUpdateIn(BaseModel):
    current_password: str = Field(..., min_length=6, max_length=20)
    new_password: str = Field(..., min_length=6, max_length=20)
    confirm_password: str = Field(..., min_length=6, max_length=20)

    @model_validator(mode="after")
    def passwords_match(self):
        if self.new_password != self.confirm_password:
            raise ValueError("两次新密码输入不一致")
        if self.current_password == self.new_password:
            raise ValueError("新密码不能与当前密码相同")
        return self


class LoginRecordOut(BaseModel):
    id: int
    login_at: datetime
    ip_address: str
    user_agent: str


class AccountCancelIn(BaseModel):
    password: str = Field(..., min_length=6, max_length=20)
    confirmation: str
