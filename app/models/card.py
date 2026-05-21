import json

from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from app.database import Base


class CardTemplate(Base):
    """贺卡模板"""
    __tablename__ = "card_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False)
    type = Column(String(16), nullable=False)  # flip / auto / template
    description = Column(String(256), default="")
    style_config = Column(Text, default="{}")  # JSON: colors, layout params
    min_level = Column(Integer, default=1)  # 所需最低等级
    preview_image = Column(String(512), default="")
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)


class Card(Base):
    """已生成的贺卡"""
    __tablename__ = "cards"

    id = Column(Integer, primary_key=True, autoincrement=True)
    couple_id = Column(Integer, ForeignKey("couples.id"), nullable=False, index=True)
    template_id = Column(Integer, ForeignKey("card_templates.id"), nullable=True)
    type = Column(String(16), nullable=False)  # flip / auto / template
    title = Column(String(128), default="")
    message = Column(Text, default="")  # 用户填写的祝福语
    data_snapshot = Column(Text, default="{}")  # JSON: 生成时的数据快照
    image_url = Column(String(512), default="")  # 生成的图片(小程序侧生成)
    trigger_event = Column(String(64), default="")  # 触发事件: anniversary/plan_done/manual
    event_ref_id = Column(Integer, nullable=True)  # 关联的事件ID
    read = Column(Integer, default=0)  # 对方是否已看
    created_at = Column(DateTime, default=datetime.now)
