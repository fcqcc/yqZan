import random
import string
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nickname = Column(String(32), nullable=False, index=True)
    birthday = Column(String(10), default="")
    gender = Column(String(6), default="")
    password_hash = Column(String(128), nullable=False)
    invite_code = Column(String(6), unique=True, index=True, nullable=False)
    couple_id = Column(Integer, ForeignKey("couples.id"), nullable=True, index=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)

    couple = relationship("Couple", backref="members", foreign_keys=[couple_id])

    @staticmethod
    def generate_invite_code() -> str:
        chars = string.ascii_uppercase + string.digits
        return "".join(random.choices(chars, k=6))
