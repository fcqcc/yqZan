import hashlib
from datetime import datetime, timedelta

import httpx
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
security = HTTPBearer()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: int) -> str:
    expire = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRE_HOURS)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def get_current_user(
    cred: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = jwt.decode(
            cred.credentials, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError, TypeError):
        raise HTTPException(status_code=401, detail="无效的 token")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user


def wx_code_to_openid(code: str) -> str:
    """将 wx.login() 的 code 交换为 openid

    当 WECHAT_MOCK_ENABLED=True 时（开发环境），直接使用 code 的 md5 作为 openid，
    跳过真实的微信 API 调用。上线前请配置 WECHAT_APPID/WECHAT_SECRET 并关闭 mock。
    """
    if settings.WECHAT_MOCK_ENABLED:
        # 开发环境：使用固定 openid，避免每次 wx.login() 生成不同用户
        return "mock_dev_user"

    # 生产环境：调用微信 API
    url = (
        f"https://api.weixin.qq.com/sns/jscode2session"
        f"?appid={settings.WECHAT_APPID}"
        f"&secret={settings.WECHAT_SECRET}"
        f"&js_code={code}"
        f"&grant_type=authorization_code"
    )
    try:
        resp = httpx.get(url, timeout=10)
        data = resp.json()
    except Exception as e:
        raise HTTPException(502, f"微信登录服务异常: {e}")

    if "openid" not in data:
        err = data.get("errmsg", "微信登录失败")
        raise HTTPException(400, f"微信登录失败: {err}")

    return data["openid"]


def get_or_create_user_by_openid(openid: str, db: Session) -> User:
    """根据 openid 查找用户，不存在则创建"""
    user = db.query(User).filter(User.openid == openid).first()
    if user:
        return user

    # 创建新用户
    code = User.generate_invite_code(openid)
    # 检查邀请码冲突（理论上 md5 前 6 位可能有冲突）
    existing = db.query(User).filter(User.invite_code == code).first()
    if existing:
        # 极低概率冲突，追加后缀
        code = code + "X"

    user = User(
        openid=openid,
        nickname=openid,  # 默认用 openid 作为昵称
        password_hash='',  # 微信登录无需密码
        invite_code=code,
    )
    db.add(user)
    db.flush()

    # 自动创建个人 Couple（附赠5张抽奖券）
    from app.models.couple import Couple

    couple = Couple(status="active", draw_tickets=5)
    db.add(couple)
    db.flush()
    user.couple_id = couple.id

    db.commit()
    db.refresh(user)
    return user
