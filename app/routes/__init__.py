from app.routes.user import router as user_router
from app.routes.couple import router as couple_router
from app.routes.plan import router as plan_router
from app.routes.extra import router as extra_router

__all__ = ["user_router", "couple_router", "plan_router", "extra_router"]
