from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String

from app.database import Base


class AchievementProgress(Base):
    __tablename__ = "achievement_progress"

    id = Column(Integer, primary_key=True, autoincrement=True)
    couple_id = Column(Integer, nullable=False, index=True)
    achievement_id = Column(String(32), nullable=False)
    unlocked = Column(Boolean, default=False)
    unlocked_at = Column(DateTime, nullable=True)
    claimed = Column(Boolean, default=False)
    claimed_at = Column(DateTime, nullable=True)
