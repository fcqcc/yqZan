from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from app.database import Base


class Level(Base):
    __tablename__ = "levels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    couple_id = Column(Integer, ForeignKey("couples.id"), unique=True, nullable=False, index=True)
    level = Column(Integer, default=1)
    current_exp = Column(Integer, default=0)
    total_exp_earned = Column(Integer, default=0)
    pending_levelups = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class LevelLog(Base):
    __tablename__ = "level_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    couple_id = Column(Integer, ForeignKey("couples.id"), nullable=False, index=True)
    amount = Column(Integer, nullable=False)
    reason = Column(String(64), default="")
    created_at = Column(DateTime, default=datetime.now)


class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    couple_id = Column(Integer, ForeignKey("couples.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    image_url = Column(String(512), default="")
    likes = Column(Integer, default=0)
    liked_by = Column(Text, default="")  # comma-separated user ids
    created_at = Column(DateTime, default=datetime.now)
