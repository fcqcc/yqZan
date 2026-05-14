from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    nickname: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=6, max_length=64)
    birthday: str = ""
    gender: str = ""


class LoginRequest(BaseModel):
    user_id: str = Field(min_length=1)
    password: str = Field(min_length=1)


class BindRequest(BaseModel):
    invite_code: str = Field(min_length=6, max_length=6)


class UserResponse(BaseModel):
    id: int
    nickname: str
    birthday: str
    gender: str
    invite_code: str
    couple_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
