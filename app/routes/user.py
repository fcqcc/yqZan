from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.user import (
    SetNicknameRequest,
    TokenResponse,
    UserResponse,
    WxLoginRequest,
)
from app.services.auth import (
    create_access_token,
    get_current_user,
    get_or_create_user_by_openid,
    wx_code_to_openid,
)

router = APIRouter(prefix="/api", tags=["用户"])


@router.post("/wx-login", response_model=TokenResponse)
def wx_login(req: WxLoginRequest, db: Session = Depends(get_db)):
    """微信登录：code → openid → 查找/创建用户 → 返回 JWT"""
    openid = wx_code_to_openid(req.code)
    user = get_or_create_user_by_openid(openid, db)
    token = create_access_token(user.id)
    return TokenResponse(access_token=token, user=user)


@router.post("/set-nickname", response_model=UserResponse)
def set_nickname(
    req: SetNicknameRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """首次进入时设置昵称"""
    if user.nickname:
        raise HTTPException(400, "昵称已设置，不可重复设置")

    # 检查昵称是否被占用
    existing = db.query(User).filter(User.nickname == req.nickname).first()
    if existing and existing.id != user.id:
        raise HTTPException(400, "该昵称已被使用")

    user.nickname = req.nickname
    db.commit()
    db.refresh(user)
    return user


@router.get("/me", response_model=UserResponse)
def get_me(user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return user
