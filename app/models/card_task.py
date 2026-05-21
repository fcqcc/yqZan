from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String

from app.database import Base


class CardTask(Base):
    """卡片任务 — 使用家务卡/服务卡等触发，双方交互完成"""
    __tablename__ = "card_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    couple_id = Column(Integer, ForeignKey("couples.id"), nullable=False, index=True)
    card_item_id = Column(String(32), nullable=False)  # chore_dishes, chore_mop, serve_me, etc.
    card_name = Column(String(64), nullable=False)  # 展示名："洗碗🧹"
    assigner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(20), default="pending")
    # pending → 等待接收方回应
    # completed_pending → 接收方声称已完成，等待发起方确认
    # completed → 发起方确认完成
    # disputed → 发起方声称未完成，退回接收方
    # declined → 接收方使用"我不要卡"无视
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    rejected = Column(Boolean, default=False)  # 原谅卡专用：被拒绝标记
    rejected_at = Column(DateTime, nullable=True)  # 拒绝时间
