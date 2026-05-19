from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text

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
    stamped_by = Column(Text, default="")  # comma-separated user ids who stamped
    created_at = Column(DateTime, default=datetime.now)


class TaskEvent(Base):
    """系统官方任务事件定义"""
    __tablename__ = "task_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_code = Column(String(32), unique=True, nullable=False)
    title = Column(String(128), nullable=False)
    description = Column(Text, default="")
    exp_reward = Column(Integer, default=50)
    category = Column(String(32), default="romance")
    icon = Column(String(16), default="🎯")
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)


class Task(Base):
    """情侣任务"""
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    couple_id = Column(Integer, ForeignKey("couples.id"), nullable=False, index=True)
    assigner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    type = Column(String(16), default="personal")  # personal / event
    event_code = Column(String(32), nullable=True)
    category = Column(String(32), default="life")
    title = Column(String(128), nullable=False)
    note = Column(Text, default="")
    status = Column(String(16), default="pending")  # pending / accepted / verified / declined
    exp_reward = Column(Integer, default=5)
    deadline = Column(String(10), default="")
    created_at = Column(DateTime, default=datetime.now)

