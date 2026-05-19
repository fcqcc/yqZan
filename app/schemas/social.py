from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# === Level ===

class AwardExpRequest(BaseModel):
    amount: int = Field(gt=0, le=200)
    reason: str = Field(max_length=64)


class LevelResponse(BaseModel):
    level: int
    current_exp: int
    total_exp_earned: int
    next_level_exp: int
    progress_pct: float
    pending_levelups: int

    class Config:
        from_attributes = True


class LevelLogResponse(BaseModel):
    id: int
    amount: int
    reason: str
    created_at: datetime

    class Config:
        from_attributes = True


# === Note ===

class NoteCreate(BaseModel):
    content: str = Field(min_length=1, max_length=500)
    image_url: str = ""


class NoteResponse(BaseModel):
    id: int
    content: str
    image_url: str
    likes: int
    liked: bool = False
    stamped: bool = False
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class NoteListResponse(BaseModel):
    notes: List[NoteResponse]


# === Task ===

class TaskCreate(BaseModel):
    assignee_id: int
    title: str = Field(min_length=1, max_length=128)
    note: str = ""
    category: str = "life"
    deadline: str = ""


class TaskEventAccept(BaseModel):
    event_code: str = Field(min_length=1)


class TaskResponse(BaseModel):
    id: int
    assigner_id: int
    assignee_id: int
    type: str
    category: str
    title: str
    note: str
    status: str
    exp_reward: int
    deadline: str
    created_at: datetime

    class Config:
        from_attributes = True


class TaskEventResponse(BaseModel):
    id: int
    event_code: str
    title: str
    description: str
    exp_reward: int
    category: str
    icon: str
    active: bool

    class Config:
        from_attributes = True
