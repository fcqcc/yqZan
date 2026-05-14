from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routes import couple_router, extra_router, plan_router, social_router, user_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Couple Promise API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user_router)
app.include_router(couple_router)
app.include_router(plan_router)
app.include_router(extra_router)
app.include_router(social_router)


@app.get("/health")
def health():
    return {"status": "ok"}
