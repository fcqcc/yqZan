from app.routes.user import router as user_router
from app.routes.couple import router as couple_router
from app.routes.plan import router as plan_router
from app.routes.extra import router as extra_router
from app.routes.social import router as social_router
from app.routes.card import router as card_router
from app.routes.admin import router as admin_router

__all__ = [
    "user_router", "couple_router", "plan_router",
    "extra_router", "social_router", "card_router",
    "admin_router",
]
