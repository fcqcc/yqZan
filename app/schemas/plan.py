from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# === Plan ===

class PlanCreate(BaseModel):
    title: str = Field(min_length=1, max_length=128)
    target_amount: float = Field(gt=0)
    start_date: str = ""
    end_date: str = ""
    unlimited: bool = False


class PlanUpdate(BaseModel):
    title: Optional[str] = None
    target_amount: Optional[float] = None
    end_date: Optional[str] = None


class DeliverRequest(BaseModel):
    amount: float = Field(gt=0)
    note: str = ""


class DeliveryResponse(BaseModel):
    id: int
    amount: float
    note: str
    created_at: datetime

    class Config:
        from_attributes = True


class PlanResponse(BaseModel):
    id: int
    title: str
    target_amount: float
    current_amount: float
    start_date: str
    end_date: str
    unlimited: bool = False
    done: bool
    deliveries: List[DeliveryResponse] = []
    notify_status: str = ""
    remaining_days: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


# === Wish ===

class WishCreate(BaseModel):
    title: str = Field(min_length=1, max_length=128)
    description: str = ""
    image_url: str = ""


class WishUpdate(BaseModel):
    status: Optional[str] = None  # promised / in_progress / fulfilled
    description: Optional[str] = None
    image_url: Optional[str] = None
    fulfilled_date: Optional[str] = None


class WishResponse(BaseModel):
    id: int
    title: str
    description: str
    image_url: str
    status: str
    fulfilled_date: str
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True
