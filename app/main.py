import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.router import router as auth_router
from app.config import get_settings
from app.orders.router import router as orders_router
from app.profiles.router import router as profiles_router
from app.scheduler.jobs import start_scheduler, stop_scheduler
from app.users.router import router as users_router

log = structlog.get_logger()
settings = get_settings()

app = FastAPI(
    title="Swiggy Mom",
    description="Proactive meal ordering agent — 3 macro-scored options, 45 min before every meal.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if not settings.is_production else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(users_router, prefix="/users", tags=["users"])
app.include_router(profiles_router, prefix="/profile", tags=["profile"])
app.include_router(orders_router, prefix="/orders", tags=["orders"])


@app.on_event("startup")
async def startup() -> None:
    log.info("swiggy_mom.startup", environment=settings.environment)
    start_scheduler()


@app.on_event("shutdown")
async def shutdown() -> None:
    log.info("swiggy_mom.shutdown")
    stop_scheduler()


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok", "version": "0.1.0"}


@app.get("/suggestions/now", tags=["agent"])
async def suggestions_now() -> dict[str, object]:
    """Manual trigger for demo/debug. Runs the full suggestion pipeline immediately."""
    from app.agent.orchestrator import build_suggestions_for_demo

    return await build_suggestions_for_demo()


@app.post("/feedback/cheat-meal", tags=["agent"])
async def cheat_meal() -> dict[str, str]:
    """Suspend macro/lifestyle filters for the next meal only."""
    return {"status": "cheat_mode_activated", "resets_after": "next_meal_order"}


@app.post("/feedback/skip", tags=["agent"])
async def skip_suggestion() -> dict[str, str]:
    """Explicit skip signal — skip_learner will process asynchronously."""
    return {"status": "skip_recorded"}


@app.get("/reports/weekly", tags=["reports"])
async def weekly_report() -> dict[str, object]:
    """Macro + spend summary for the past 7 days."""
    return {
        "period": "last_7_days",
        "total_protein_g": 0,
        "avg_daily_protein_g": 0,
        "total_spend_inr": 0,
        "orders_count": 0,
        "note": "Connect your Swiggy account to see real data.",
    }
