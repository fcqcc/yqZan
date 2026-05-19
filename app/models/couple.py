from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from app.database import Base


class Couple(Base):
    __tablename__ = "couples"

    id = Column(Integer, primary_key=True, autoincrement=True)
    status = Column(String(16), default="active")  # active / archived
    draw_tickets = Column(Integer, default=0)  # 抽卡券数量
    created_at = Column(DateTime, default=datetime.now)
    archived_at = Column(DateTime, nullable=True)
