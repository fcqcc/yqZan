from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from app.database import Base


class Couple(Base):
    __tablename__ = "couples"

    id = Column(Integer, primary_key=True, autoincrement=True)
    status = Column(String(16), default="active")  # active / archived
    draw_tickets = Column(Integer, default=0)
    spark_count = Column(Integer, default=0)  # 当日火化数
    max_spark_count = Column(Integer, default=0)  # 历史最高火花
    spark_status = Column(String(8), default="active")  # active / gray
    created_at = Column(DateTime, default=datetime.now)
    archived_at = Column(DateTime, nullable=True)
