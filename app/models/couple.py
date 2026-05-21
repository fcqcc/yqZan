from datetime import datetime

from sqlalchemy import Column, Date, DateTime, Integer, String

from app.database import Base


class Couple(Base):
    __tablename__ = "couples"

    id = Column(Integer, primary_key=True, autoincrement=True)
    status = Column(String(16), default="active")  # active / archived
    draw_tickets = Column(Integer, default=0)
    spark_count = Column(Integer, default=0)  # 当日火化数
    max_spark_count = Column(Integer, default=0)  # 历史最高火花
    spark_status = Column(String(8), default="active")  # active / gray
    shards = Column(Integer, default=0)  # 积分
    gacha_pity = Column(Integer, default=0)  # 距离上次SSR+的抽卡次数（低保计数）
    candy_date = Column(Date, nullable=True)  # 亲密糖果使用日期
    candy_count = Column(Integer, default=0)  # 当日已使用糖果数
    created_at = Column(DateTime, default=datetime.now)
    archived_at = Column(DateTime, nullable=True)
