from fastapi import APIRouter

from app.dependencies import CurrentUserDep, DbDep
from app.users import service
from app.users.schemas import UserOut

router = APIRouter()


@router.get("/me", response_model=UserOut)
async def get_me(user_id: CurrentUserDep, db: DbDep) -> UserOut:
    user = await service.get_user_by_swiggy_id(db, user_id)
    if user is None:
        user = await service.get_or_create_user(db, user_id)
    return UserOut.model_validate(user)
