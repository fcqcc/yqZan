import httpx
from app.config import settings
from app.database import SessionLocal
from app.services.auth import wx_code_to_openid, get_or_create_user_by_openid

print("DATABASE_URL:", settings.DATABASE_URL)
try:
    db = SessionLocal()
    oid = wx_code_to_openid("test123")
    user = get_or_create_user_by_openid(oid, db)
    print("DB OK user_id:", user.id)
    db.close()
except Exception as e:
    import traceback
    traceback.print_exc()

r = httpx.post("http://127.0.0.1:5000/api/wx-login", json={"code": "test123"})
print("HTTP", r.status_code, r.text)
