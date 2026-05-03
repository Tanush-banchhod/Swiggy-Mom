import uuid
from datetime import datetime

from pydantic import BaseModel


class UserOut(BaseModel):
    id: uuid.UUID
    swiggy_user_id: str
    created_at: datetime

    model_config = {"from_attributes": True}
