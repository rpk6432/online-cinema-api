from fastapi import APIRouter

from routes.auth import router as auth_router
from routes.certifications import router as certifications_router
from routes.directors import router as directors_router
from routes.genres import router as genres_router
from routes.profiles import router as profiles_router
from routes.stars import router as stars_router
from routes.users import router as users_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(profiles_router)
router.include_router(users_router)
router.include_router(genres_router)
router.include_router(stars_router)
router.include_router(directors_router)
router.include_router(certifications_router)
