from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import HTMLResponse, JSONResponse
from loguru import logger
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy.exc import IntegrityError

from admin import setup_admin
from core import AppError, settings, setup_logging
from core.dependencies import verify_admin_basic
from core.rate_limit import limiter
from database.seed import seed_user_groups
from database.session import async_session
from routes import router


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    setup_logging(log_level=settings.log_level, json_format=not settings.debug)
    async with async_session() as db:
        await seed_user_groups(db)
    logger.info("Application starting up")
    yield
    logger.info("Application shutting down")


app = FastAPI(
    title=settings.app_title,
    debug=settings.debug,
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
)

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

setup_admin(app)
app.include_router(router)


@app.exception_handler(AppError)
async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(IntegrityError)
async def integrity_error_handler(
    _request: Request, _exc: IntegrityError
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={"detail": "Resource already exists"},
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, _exc: Exception) -> JSONResponse:
    logger.exception(
        "Unhandled exception",
        method=request.method,
        path=str(request.url),
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/docs", include_in_schema=False)
async def docs(_: None = Depends(verify_admin_basic)) -> HTMLResponse:
    """Swagger UI — admin only."""
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title=f"{app.title} — Docs",
    )


@app.get("/redoc", include_in_schema=False)
async def redoc(_: None = Depends(verify_admin_basic)) -> HTMLResponse:
    """ReDoc — admin only."""
    return get_redoc_html(
        openapi_url="/openapi.json",
        title=f"{app.title} — ReDoc",
    )
