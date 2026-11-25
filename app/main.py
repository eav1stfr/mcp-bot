import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from alembic.config import Config
from fastapi import APIRouter, FastAPI

from alembic import command
from app.config.base import CONFIG, fastapi_config
from app.movies.router import movies_router
from app.users.router import users_router
from app.wishlists.router import wishlists_router

_logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    if CONFIG.RUN_MIGRATIONS_UPON_LAUNCH:
        _logger.info("Run alembic upgrade head")
        try:
            command.upgrade(Config("alembic.ini"), "head")
        except Exception as e:
            _logger.error("Error running database migrations: %s", e)
            raise SystemError(f"Migrations failed: {e!s}") from e
    yield


app = FastAPI(**fastapi_config, lifespan=lifespan)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    """Liveness check; doesn't touch the database"""
    return {"status": "ok"}


main_router = APIRouter(prefix=CONFIG.GLOBAL_API_PREFIX)

main_router.include_router(users_router)
main_router.include_router(wishlists_router)
main_router.include_router(movies_router)
app.include_router(main_router)
