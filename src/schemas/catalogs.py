from pydantic import BaseModel, ConfigDict


class CertificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class CertificationCreateRequest(BaseModel):
    name: str


class GenreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class GenreWithCountResponse(GenreResponse):
    movie_count: int = 0


class GenreCreateRequest(BaseModel):
    name: str


class StarResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class StarCreateRequest(BaseModel):
    name: str


class DirectorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class DirectorCreateRequest(BaseModel):
    name: str
