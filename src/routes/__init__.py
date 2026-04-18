from fastapi import APIRouter

from routes.auth import router as auth_router
from routes.profiles import router as profiles_router
from routes.users import router as users_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(profiles_router)
router.include_router(users_router)
