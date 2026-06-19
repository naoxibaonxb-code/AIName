from pydantic import BaseModel, ConfigDict, Field


class AdminUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    username: str
    role: str
    is_active: bool


class AdminUserListOut(BaseModel):
    items: list[AdminUserOut]
    total: int
    page: int
    page_size: int


class UserStatusIn(BaseModel):
    is_active: bool = Field(..., description="用户是否可以登录和访问受保护接口")
