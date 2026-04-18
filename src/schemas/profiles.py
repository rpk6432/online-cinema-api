from datetime import date

from pydantic import BaseModel, ConfigDict

from models.user import GenderEnum


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    first_name: str | None
    last_name: str | None
    avatar: str | None
    gender: str | None
    date_of_birth: date | None
    info: str | None


class ProfileUpdateRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    gender: GenderEnum | None = None
    date_of_birth: date | None = None
    info: str | None = None
