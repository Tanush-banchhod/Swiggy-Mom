"""Initial schema — users, profiles, meal tracking

Revision ID: 0001
Revises:
Create Date: 2026-05-03
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("swiggy_user_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("swiggy_user_id"),
    )
    op.create_index("ix_users_swiggy_user_id", "users", ["swiggy_user_id"])

    op.create_table(
        "nutrition_goals",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.swiggy_user_id"), nullable=False),
        sa.Column("protein_g_daily", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("calorie_ceiling", sa.Integer(), nullable=True),
        sa.Column(
            "lifestyle_mode",
            sa.Enum(
                "healthy_reset", "muscle_gain", "weight_loss", "maintenance", "no_restrictions",
                name="lifestylemode",
            ),
            nullable=False,
            server_default="maintenance",
        ),
        sa.Column(
            "dietary_identity",
            sa.Enum("veg", "non_veg", "eggetarian", "vegan", "jain", name="dietaryidentity"),
            nullable=False,
            server_default="non_veg",
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    op.create_table(
        "allergy_blocks",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.swiggy_user_id"), nullable=False),
        sa.Column("ingredient_name", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "taste_dislikes",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.swiggy_user_id"), nullable=False),
        sa.Column("ingredient_name", sa.String(), nullable=False),
        sa.Column("skip_count", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "location_schedule",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.swiggy_user_id"), nullable=False),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("address_id", sa.String(), nullable=False),
        sa.Column("address_label", sa.String(), nullable=False, server_default=""),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "meal_windows",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.swiggy_user_id"), nullable=False),
        sa.Column(
            "meal_type",
            sa.Enum("lunch", "dinner", name="mealtype"),
            nullable=False,
        ),
        sa.Column("target_time", sa.Time(), nullable=False),
        sa.Column("notify_minutes_before", sa.Integer(), nullable=False, server_default="45"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "meal_log",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.swiggy_user_id"), nullable=False),
        sa.Column("order_id", sa.String(), nullable=False),
        sa.Column("restaurant_id", sa.String(), nullable=False),
        sa.Column("protein_g", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("calories", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_inr", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ordered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("was_suggested", sa.Boolean(), nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_meal_log_user_ordered", "meal_log", ["user_id", "ordered_at"])


def downgrade() -> None:
    op.drop_table("meal_log")
    op.drop_table("meal_windows")
    op.drop_table("location_schedule")
    op.drop_table("taste_dislikes")
    op.drop_table("allergy_blocks")
    op.drop_table("nutrition_goals")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS lifestylemode")
    op.execute("DROP TYPE IF EXISTS dietaryidentity")
    op.execute("DROP TYPE IF EXISTS mealtype")
