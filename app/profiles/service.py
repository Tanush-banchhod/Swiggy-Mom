import structlog
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.profiles.models import (
    AllergyBlock,
    LocationSchedule,
    MealLog,
    MealType,
    MealWindow,
    NutritionGoal,
    TasteDislike,
)
from app.profiles.schemas import (
    FullProfileOut,
    LocationScheduleIn,
    MealWindowEntry,
    MealWindowIn,
    NutritionGoalIn,
    NutritionGoalOut,
)

log = structlog.get_logger()

_AUTO_DISLIKE_THRESHOLD = 3  # skips in 30 days → auto dislike


async def upsert_nutrition_goal(db: AsyncSession, user_id: str, data: NutritionGoalIn) -> NutritionGoal:
    result = await db.execute(select(NutritionGoal).where(NutritionGoal.user_id == user_id))
    goal = result.scalar_one_or_none()
    if goal is None:
        goal = NutritionGoal(user_id=user_id)
        db.add(goal)

    goal.protein_g_daily = data.protein_g_daily
    goal.calorie_ceiling = data.calorie_ceiling
    goal.lifestyle_mode = data.lifestyle_mode
    goal.dietary_identity = data.dietary_identity
    await db.flush()
    log.info("profile.nutrition_goal_upserted", user_id=user_id)
    return goal


async def set_allergy_blocks(db: AsyncSession, user_id: str, ingredients: list[str]) -> list[str]:
    await db.execute(delete(AllergyBlock).where(AllergyBlock.user_id == user_id))
    for ingredient in ingredients:
        db.add(AllergyBlock(user_id=user_id, ingredient_name=ingredient.lower().strip()))
    await db.flush()
    return [i.lower().strip() for i in ingredients]


async def get_allergy_blocks(db: AsyncSession, user_id: str) -> list[str]:
    result = await db.execute(select(AllergyBlock).where(AllergyBlock.user_id == user_id))
    return [row.ingredient_name for row in result.scalars()]


async def set_taste_dislikes(db: AsyncSession, user_id: str, ingredients: list[str]) -> list[str]:
    await db.execute(delete(TasteDislike).where(TasteDislike.user_id == user_id))
    for ingredient in ingredients:
        db.add(TasteDislike(user_id=user_id, ingredient_name=ingredient.lower().strip()))
    await db.flush()
    return [i.lower().strip() for i in ingredients]


async def get_taste_dislikes(db: AsyncSession, user_id: str) -> list[str]:
    result = await db.execute(select(TasteDislike).where(TasteDislike.user_id == user_id))
    return [row.ingredient_name for row in result.scalars()]


async def set_location_schedule(db: AsyncSession, user_id: str, data: LocationScheduleIn) -> None:
    await db.execute(delete(LocationSchedule).where(LocationSchedule.user_id == user_id))
    for entry in data.schedule:
        db.add(
            LocationSchedule(
                user_id=user_id,
                day_of_week=entry.day_of_week,
                address_id=entry.address_id,
                address_label=entry.address_label,
            )
        )
    await db.flush()


async def get_address_for_today(db: AsyncSession, user_id: str, day_of_week: int) -> str | None:
    """Resolve which Swiggy address_id to use for `day_of_week` (0=Mon)."""
    result = await db.execute(
        select(LocationSchedule).where(
            LocationSchedule.user_id == user_id,
            LocationSchedule.day_of_week == day_of_week,
        )
    )
    row = result.scalar_one_or_none()
    return row.address_id if row else None


async def set_meal_windows(db: AsyncSession, user_id: str, data: MealWindowIn) -> None:
    await db.execute(delete(MealWindow).where(MealWindow.user_id == user_id))
    for entry in data.windows:
        db.add(
            MealWindow(
                user_id=user_id,
                meal_type=entry.meal_type,
                target_time=entry.target_time,
                notify_minutes_before=entry.notify_minutes_before,
            )
        )
    await db.flush()


async def get_meal_windows(db: AsyncSession, user_id: str) -> list[MealWindowEntry]:
    result = await db.execute(select(MealWindow).where(MealWindow.user_id == user_id))
    return [
        MealWindowEntry(
            meal_type=row.meal_type,
            target_time=row.target_time,
            notify_minutes_before=row.notify_minutes_before,
        )
        for row in result.scalars()
    ]


async def increment_skip(db: AsyncSession, user_id: str, ingredient: str) -> None:
    """Passive skip learning — auto-promote to dislike after threshold."""
    result = await db.execute(
        select(TasteDislike).where(
            TasteDislike.user_id == user_id,
            TasteDislike.ingredient_name == ingredient.lower(),
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        db.add(TasteDislike(user_id=user_id, ingredient_name=ingredient.lower(), skip_count=1))
    else:
        row.skip_count += 1
        if row.skip_count >= _AUTO_DISLIKE_THRESHOLD:
            log.info("skip_learner.auto_dislike", user_id=user_id, ingredient=ingredient)
    await db.flush()


async def get_full_profile(db: AsyncSession, user_id: str) -> FullProfileOut:
    result = await db.execute(select(NutritionGoal).where(NutritionGoal.user_id == user_id))
    goal_row = result.scalar_one_or_none()
    goal = NutritionGoalOut.model_validate(goal_row) if goal_row else None

    allergy_blocks = await get_allergy_blocks(db, user_id)
    taste_dislikes = await get_taste_dislikes(db, user_id)
    meal_windows = await get_meal_windows(db, user_id)

    onboarding_complete = (
        goal is not None
        and len(meal_windows) > 0
    )

    return FullProfileOut(
        nutrition_goal=goal,
        allergy_blocks=allergy_blocks,
        taste_dislikes=taste_dislikes,
        meal_windows=meal_windows,
        onboarding_complete=onboarding_complete,
    )
