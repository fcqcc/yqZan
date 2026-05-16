from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text

from app.database import Base


class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    couple_id = Column(Integer, ForeignKey("couples.id"), nullable=False, index=True)
    title = Column(String(128), nullable=False)
    target_amount = Column(Float, default=0)
    current_amount = Column(Float, default=0)
    start_date = Column(String(10), default="")
    end_date = Column(String(10), default="")
    unlimited = Column(Boolean, default=False)
    done = Column(Boolean, default=False)
    notify_status = Column(Text, default="")  # JSON: {"user_X": "unread|read", "user_Y": "unread|read"}
    created_at = Column(DateTime, default=datetime.now)


class Delivery(Base):
    __tablename__ = "deliveries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    note = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now)


class Wish(Base):
    __tablename__ = "wishes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    couple_id = Column(Integer, ForeignKey("couples.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(128), nullable=False)
    description = Column(Text, default="")
    image_url = Column(String(512), default="")
    status = Column(String(16), default="promised")  # promised / in_progress / fulfilled
    fulfilled_date = Column(String(10), default="")
    created_at = Column(DateTime, default=datetime.now)
