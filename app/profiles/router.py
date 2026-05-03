from fastapi import APIRouter

from app.dependencies import CurrentUserDep, DbDep
from app.profiles import service
from app.profiles.schemas import (
    AllergyBlockIn,
    FullProfileOut,
    LifestyleModeIn,
    LocationScheduleIn,
    MealWindowIn,
    NutritionGoalIn,
    NutritionGoalOut,
    TasteDislikeIn,
)
from app.profiles.models import LifestyleMode

router = APIRouter()


@router.get("", response_model=FullProfileOut)
async def get_profile(user_id: CurrentUserDep, db: DbDep) -> FullProfileOut:
    return await service.get_full_profile(db, user_id)


@router.put("/goals", response_model=NutritionGoalOut)
async def set_goals(user_id: CurrentUserDep, db: DbDep, data: NutritionGoalIn) -> NutritionGoalOut:
    goal = await service.upsert_nutrition_goal(db, user_id, data)
    return NutritionGoalOut.model_validate(goal)


@router.put("/allergies")
async def set_allergies(user_id: CurrentUserDep, db: DbDep, data: AllergyBlockIn) -> dict[str, object]:
    blocked = await service.set_allergy_blocks(db, user_id, data.ingredients)
    return {"allergy_blocks": blocked, "count": len(blocked)}


@router.put("/dislikes")
async def set_dislikes(user_id: CurrentUserDep, db: DbDep, data: TasteDislikeIn) -> dict[str, object]:
    dislikes = await service.set_taste_dislikes(db, user_id, data.ingredients)
    return {"taste_dislikes": dislikes, "count": len(dislikes)}


@router.put("/schedule")
async def set_schedule(user_id: CurrentUserDep, db: DbDep, data: LocationScheduleIn) -> dict[str, str]:
    await service.set_location_schedule(db, user_id, data)
    return {"status": "updated"}


@router.put("/meal-windows")
async def set_meal_windows(user_id: CurrentUserDep, db: DbDep, data: MealWindowIn) -> dict[str, str]:
    await service.set_meal_windows(db, user_id, data)
    return {"status": "updated"}


@router.put("/lifestyle")
async def set_lifestyle(user_id: CurrentUserDep, db: DbDep, data: LifestyleModeIn) -> dict[str, str]:
    from app.profiles.schemas import NutritionGoalIn
    from app.profiles.models import DietaryIdentity
    import sqlalchemy as sa
    from app.profiles.models import NutritionGoal

    result = await db.execute(sa.select(NutritionGoal).where(NutritionGoal.user_id == user_id))
    goal = result.scalar_one_or_none()
    if goal:
        goal.lifestyle_mode = data.lifestyle_mode
    else:
        db.add(NutritionGoal(user_id=user_id, lifestyle_mode=data.lifestyle_mode))
    await db.flush()
    return {"status": "updated", "lifestyle_mode": data.lifestyle_mode.value}
