import enum
import uuid
from datetime import datetime, time, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Time,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LifestyleMode(str, enum.Enum):
    healthy_reset = "healthy_reset"
    muscle_gain = "muscle_gain"
    weight_loss = "weight_loss"
    maintenance = "maintenance"
    no_restrictions = "no_restrictions"


class MealType(str, enum.Enum):
    lunch = "lunch"
    dinner = "dinner"
    snack = "snack"

class DietaryIdentity(str, enum.Enum):
    veg = "veg"
    non_veg = "non_veg"
    eggetarian = "eggetarian"
    vegan = "vegan"
    jain = "jain"


class NutritionGoal(Base):
    __tablename__ = "nutrition_goals"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.swiggy_user_id"), unique=True)
    protein_g_daily: Mapped[int] = mapped_column(Integer, default=100)
    calorie_ceiling: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lifestyle_mode: Mapped[LifestyleMode] = mapped_column(
        Enum(LifestyleMode), default=LifestyleMode.maintenance
    )
    dietary_identity: Mapped[DietaryIdentity] = mapped_column(
        Enum(DietaryIdentity), default=DietaryIdentity.non_veg
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )


class AllergyBlock(Base):
    __tablename__ = "allergy_blocks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.swiggy_user_id"))
    ingredient_name: Mapped[str] = mapped_column(String)


class TasteDislike(Base):
    __tablename__ = "taste_dislikes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.swiggy_user_id"))
    ingredient_name: Mapped[str] = mapped_column(String)
    skip_count: Mapped[int] = mapped_column(Integer, default=0)


class LocationSchedule(Base):
    __tablename__ = "location_schedule"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.swiggy_user_id"))
    day_of_week: Mapped[int] = mapped_column(Integer)  # 0=Mon, 6=Sun
    address_id: Mapped[str] = mapped_column(String)
    address_label: Mapped[str] = mapped_column(String, default="")


class MealWindow(Base):
    __tablename__ = "meal_windows"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.swiggy_user_id"))
    meal_type: Mapped[MealType] = mapped_column(Enum(MealType))
    target_time: Mapped[time] = mapped_column(Time)
    notify_minutes_before: Mapped[int] = mapped_column(Integer, default=45)


class MealLog(Base):
    __tablename__ = "meal_log"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.swiggy_user_id"))
    order_id: Mapped[str] = mapped_column(String)
    restaurant_id: Mapped[str] = mapped_column(String)
    protein_g: Mapped[int] = mapped_column(Integer, default=0)
    calories: Mapped[int] = mapped_column(Integer, default=0)
    cost_inr: Mapped[int] = mapped_column(Integer, default=0)
    ordered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    was_suggested: Mapped[bool] = mapped_column(Boolean, default=True)
