from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.user import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/api", tags=["用户"])


@router.post("/register", response_model=TokenResponse)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.nickname == req.nickname).first()
    if existing:
        raise HTTPException(400, "昵称已被使用")

    for _ in range(5):
        code = User.generate_invite_code()
        if not db.query(User).filter(User.invite_code == code).first():
            break
    else:
        raise HTTPException(500, "邀请码生成失败，请重试")

    user = User(
        nickname=req.nickname,
        password_hash=hash_password(req.password),
        birthday=req.birthday,
        gender=req.gender,
        invite_code=code,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)
    return TokenResponse(access_token=token, user=user)


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        (User.nickname == req.user_id) | (User.invite_code == req.user_id)
    ).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(401, "账号或密码错误")

    token = create_access_token(user.id)
    return TokenResponse(access_token=token, user=user)


@router.get("/me", response_model=UserResponse)
def get_me(user: User = Depends(get_current_user)):
    return user
