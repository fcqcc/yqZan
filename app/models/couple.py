from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from app.database import Base


class Couple(Base):
    __tablename__ = "couples"

    id = Column(Integer, primary_key=True, autoincrement=True)
    status = Column(String(16), default="active")  # active / archived
    created_at = Column(DateTime, default=datetime.now)
    archived_at = Column(DateTime, nullable=True)
