from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class WxLoginRequest(BaseModel):
    code: str = Field(min_length=1, description="wx.login() 返回的临时 code")


class SetNicknameRequest(BaseModel):
    nickname: str = Field(min_length=1, max_length=32)


class BindRequest(BaseModel):
    invite_code: str = Field(min_length=6, max_length=6)


class UserResponse(BaseModel):
    id: int
    nickname: Optional[str] = None
    has_nickname: bool = False
    birthday: str = ""
    gender: str = ""
    invite_code: str
    couple_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
