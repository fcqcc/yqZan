from app.routes.user import router as user_router
from app.routes.couple import router as couple_router
from app.routes.plan import router as plan_router
from app.routes.extra import router as extra_router
from app.routes.social import router as social_router
from app.routes.card import router as card_router
from app.routes.checkin import router as checkin_router
from app.routes.achievement import router as achievement_router
from app.routes.admin import router as admin_router
from app.routes.pet import router as pet_router
from app.routes.gacha import router as gacha_router
from app.routes.card_task import router as card_task_router
from app.routes.store_admin import router as store_admin_router

__all__ = [
    "user_router", "couple_router", "plan_router",
    "extra_router", "social_router", "card_router",
    "admin_router", "achievement_router", "checkin_router", "pet_router", "gacha_router",
    "card_task_router",
    "store_admin_router",
]
