import hashlib
import random
import string
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    openid = Column(String(64), unique=True, index=True, nullable=False)
    nickname = Column(String(32), nullable=True, index=True)
    birthday = Column(String(10), default="")
    gender = Column(String(6), default="")
    password_hash = Column(String(128), nullable=True)
    invite_code = Column(String(6), unique=True, index=True, nullable=False)
    couple_id = Column(Integer, ForeignKey("couples.id"), nullable=True, index=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)

    couple = relationship("Couple", backref="members", foreign_keys=[couple_id])

    @property
    def has_nickname(self) -> bool:
        return bool(self.nickname)

    @staticmethod
    def generate_invite_code(openid: str) -> str:
        """基于 openid 生成确定性 6 位唯一邀请码"""
        h = hashlib.md5(openid.encode()).hexdigest().upper()
        return h[:6]
