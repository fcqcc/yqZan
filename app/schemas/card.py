from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class TemplateResponse(BaseModel):
    id: int
    name: str
    type: str
    description: str
    style_config: Any
    min_level: int
    preview_image: str
    sort_order: int

    @field_validator("style_config", mode="before")
    @classmethod
    def parse_style_config(cls, v):
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return {}
        return v

    class Config:
        from_attributes = True


class GenerateCardRequest(BaseModel):
    template_id: int
    title: str = ""
    message: str = ""
    trigger_event: str = "manual"
    event_ref_id: Optional[int] = None


class CardResponse(BaseModel):
    id: int
    template_id: Optional[int]
    type: str
    title: str
    message: str
    data_snapshot: Dict
    image_url: str
    trigger_event: str
    read: int
    created_at: datetime

    class Config:
        from_attributes = True


class CardListResponse(BaseModel):
    cards: List[CardResponse]


class CardSnapshotRequest(BaseModel):
    """获取生成总结卡所需的数据快照"""
    pass
