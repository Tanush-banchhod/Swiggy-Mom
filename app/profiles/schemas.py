from datetime import time

from pydantic import BaseModel, Field

from app.profiles.models import DietaryIdentity, LifestyleMode, MealType


class NutritionGoalIn(BaseModel):
    protein_g_daily: int = Field(ge=0, le=500, description="Daily protein target in grams")
    calorie_ceiling: int | None = Field(None, ge=0, description="Max daily calories (null = no limit)")
    lifestyle_mode: LifestyleMode = LifestyleMode.maintenance
    dietary_identity: DietaryIdentity = DietaryIdentity.non_veg


class NutritionGoalOut(NutritionGoalIn):
    model_config = {"from_attributes": True}


class AllergyBlockIn(BaseModel):
    ingredients: list[str] = Field(min_length=1, description="List of ingredients to hard-block")


class TasteDislikeIn(BaseModel):
    ingredients: list[str] = Field(min_length=1)


class LocationScheduleEntry(BaseModel):
    day_of_week: int = Field(ge=0, le=6, description="0=Mon … 6=Sun")
    address_id: str
    address_label: str = ""


class LocationScheduleIn(BaseModel):
    schedule: list[LocationScheduleEntry]


class MealWindowEntry(BaseModel):
    meal_type: MealType
    target_time: time
    notify_minutes_before: int = Field(default=45, ge=5, le=120)


class MealWindowIn(BaseModel):
    windows: list[MealWindowEntry]


class LifestyleModeIn(BaseModel):
    lifestyle_mode: LifestyleMode


class FullProfileOut(BaseModel):
    nutrition_goal: NutritionGoalOut | None
    allergy_blocks: list[str]
    taste_dislikes: list[str]
    meal_windows: list[MealWindowEntry]
    onboarding_complete: bool
