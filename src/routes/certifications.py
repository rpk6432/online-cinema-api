from fastapi import APIRouter, status

from core.dependencies import DBSession, ModeratorUser
from core.exceptions import AlreadyExistsError
from crud.certification import certification_crud
from schemas.catalogs import CertificationCreateRequest, CertificationResponse

router = APIRouter(prefix="/certifications", tags=["Certifications"])


@router.get("")
async def list_certifications(db: DBSession) -> list[CertificationResponse]:
    """Return all available certifications."""
    items = await certification_crud.get_multi(db, limit=100)
    return [CertificationResponse.model_validate(c) for c in items]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_certification(
    body: CertificationCreateRequest,
    user: ModeratorUser,
    db: DBSession,
) -> CertificationResponse:
    """Create a new certification (moderator only)."""
    existing = await certification_crud.get_by_name(db, body.name)
    if existing:
        raise AlreadyExistsError("Certification already exists")

    cert = await certification_crud.create(db, name=body.name)
    return CertificationResponse.model_validate(cert)
