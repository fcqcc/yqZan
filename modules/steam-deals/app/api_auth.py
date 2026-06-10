"""
API Key 鉴权依赖 — FastAPI Dependency
用法:
    @router.get("/api/today")
    async def today(key_info: dict = Depends(require_api_key)):
        ...
"""
from fastapi import Request, HTTPException, Header, Depends
from app.database import validate_api_key, track_usage


async def require_api_key(
    request: Request,
    x_api_key: str = Header(None, alias="X-API-Key"),
) -> dict:
    """验证 API Key 并记录用量，超额时返回 429"""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="缺少 X-API-Key 请求头")

    key_info = validate_api_key(x_api_key)
    if not key_info:
        raise HTTPException(status_code=403, detail="API Key 无效或已停用")

    usage = track_usage(x_api_key)

    # 超出配额
    if usage["remaining"] <= 0:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "本月调用次数已用完",
                "used": usage["used"],
                "limit": usage["limit"],
            },
        )

    return {
        "api_key": x_api_key,
        "tier": key_info["tier"],
        "usage": usage,
    }
