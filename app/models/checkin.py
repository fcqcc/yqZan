from datetime import datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer

from app.database import Base


class Checkin(Base):
    __tablename__ = "checkins"

    id = Column(Integer, primary_key=True, autoincrement=True)
    couple_id = Column(Integer, ForeignKey("couples.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    checkin_date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
