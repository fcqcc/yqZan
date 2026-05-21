from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# === ToDo ===

class ToDoCreate(BaseModel):
    scope: str = "together"  # together / alone
    type: str = "short_term"  # long_term / short_term
    title: str = Field(min_length=1, max_length=128)
    note: str = ""
    deadline: str = ""
    cycle_total: int = 0


class ToDoUpdate(BaseModel):
    title: Optional[str] = None
    note: Optional[str] = None
    deadline: Optional[str] = None
    cycle_total: Optional[int] = None
    done: Optional[bool] = None


class ToDoCheckinResponse(BaseModel):
    id: int
    user_id: int
    note: str
    created_at: datetime

    class Config:
        from_attributes = True


class ToDoResponse(BaseModel):
    id: int
    scope: str
    type: str
    title: str
    note: str
    deadline: str
    cycle_total: int
    cycle_current: int
    done: bool
    creator_id: Optional[int] = None
    checkins: List[ToDoCheckinResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True


# === Anniversary ===

class AnniversaryCreate(BaseModel):
    title: str = Field(min_length=1, max_length=64)
    date_val: str = Field(min_length=10, max_length=10)


class AnniversaryUpdate(BaseModel):
    title: Optional[str] = None
    date_val: Optional[str] = None
    remind: Optional[bool] = None


class AnniversaryResponse(BaseModel):
    id: int
    title: str
    date_val: str
    remind: bool
    created_at: datetime

    class Config:
        from_attributes = True


# === Gift ===

class GiftCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    date_val: str = ""
    note: str = ""
    price: float = 0


class GiftResponse(BaseModel):
    id: int
    name: str
    date_val: str
    note: str
    price: float
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True
