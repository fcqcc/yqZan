from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, Text

from app.database import Base


class ToDo(Base):
    __tablename__ = "todos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    couple_id = Column(Integer, ForeignKey("couples.id"), nullable=False, index=True)
    scope = Column(String(16), default="together")  # together / alone
    type = Column(String(16), default="short_term")  # long_term / short_term
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    title = Column(String(128), nullable=False)
    note = Column(Text, default="")
    deadline = Column(String(10), default="")  # short_term 截止日
    cycle_total = Column(Integer, default=0)  # long_term 目标次数
    cycle_current = Column(Integer, default=0)  # long_term 已完成次数
    done = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)


class ToDoCheckin(Base):
    __tablename__ = "todo_checkins"

    id = Column(Integer, primary_key=True, autoincrement=True)
    todo_id = Column(Integer, ForeignKey("todos.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    note = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now)


class Anniversary(Base):
    __tablename__ = "anniversaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    couple_id = Column(Integer, ForeignKey("couples.id"), nullable=False, index=True)
    title = Column(String(64), nullable=False)
    date_val = Column(String(10), nullable=False)  # YYYY-MM-DD
    remind = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)


class Gift(Base):
    __tablename__ = "gifts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    couple_id = Column(Integer, ForeignKey("couples.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(128), nullable=False)
    date_val = Column(String(10), default="")
    note = Column(Text, default="")
    price = Column(Float, default=0)
    created_at = Column(DateTime, default=datetime.now)
