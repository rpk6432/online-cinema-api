from datetime import datetime

from pydantic import BaseModel, ConfigDict

from models.user import UserGroupEnum


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    is_active: bool
    group_name: str
    created_at: datetime


class ChangeGroupRequest(BaseModel):
    group_name: UserGroupEnum
