from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, Boolean

from app.database import Base


class DrawCategory(Base):
    __tablename__ = "draw_categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    couple_id = Column(Integer, ForeignKey("couples.id"), nullable=False, index=True)
    name = Column(String(64), nullable=False)
    icon = Column(String(8), default="🎯")
    sort_order = Column(Integer, default=0)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)


class DrawItem(Base):
    __tablename__ = "draw_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category_id = Column(Integer, ForeignKey("draw_categories.id"), nullable=False, index=True)
    couple_id = Column(Integer, ForeignKey("couples.id"), nullable=False, index=True)
    content = Column(String(128), nullable=False)
    is_custom = Column(Boolean, default=False)  # False = preset, True = user-added
    used_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
