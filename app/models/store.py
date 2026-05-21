from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Product(Base):
    """数字商品"""
    __tablename__ = "store_products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False, index=True)
    description = Column(Text, default="")
    price = Column(Float, nullable=False)
    category = Column(String(32), default="其他")  # 分类: 会员卡/激活码/道具等
    stock_type = Column(String(16), default="limited")  # limited / unlimited
    status = Column(String(16), default="active")  # active / inactive
    reply_template = Column(Text, default="【{name}】已发货！你的兑换码：{code}\n使用说明：请复制兑换码到 App 内输入即可激活。")
    instructions = Column(Text, default="")
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)

    codes = relationship("CodePool", back_populates="product", lazy="dynamic")
    orders = relationship("Order", back_populates="product", lazy="dynamic")


class CodePool(Base):
    """码库 — 预生成的激活码/兑换码"""
    __tablename__ = "store_codes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("store_products.id"), nullable=False, index=True)
    code_value = Column(String(128), unique=True, nullable=False, index=True)
    status = Column(String(16), default="unused")  # unused / used / expired
    order_id = Column(Integer, ForeignKey("store_orders.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    used_at = Column(DateTime, nullable=True)

    product = relationship("Product", back_populates="codes")
    order = relationship("Order", backref="assigned_code", foreign_keys=[order_id], uselist=False)


class Order(Base):
    """订单"""
    __tablename__ = "store_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("store_products.id"), nullable=False, index=True)
    platform = Column(String(32), default="微信")  # 来源平台: 抖音/小红书/微信/快手等
    platform_username = Column(String(64), default="")  # 买家在该平台的ID
    customer_contact = Column(String(128), default="")  # 联系方式（手机/微信）
    amount = Column(Float, nullable=False)
    status = Column(String(16), default="pending")  # pending / completed / cancelled / refunded
    assigned_code_id = Column(Integer, ForeignKey("store_codes.id"), nullable=True)
    admin_note = Column(Text, default="")
    reply_text = Column(Text, default="")  # 自动生成的回复话术
    created_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime, nullable=True)

    product = relationship("Product", back_populates="orders")
