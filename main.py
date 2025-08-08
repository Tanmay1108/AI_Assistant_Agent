import logging as log
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import text

from core.config import settings
from database.postgres.postgres_database import PostgresDatabase
from routes.health import router as health_router
from routes.task import router as task_router
from routes.users import router as user_router

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

log.basicConfig(
    level=log.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = log.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup
    try:
        await PostgresDatabase.connect_db()
        # if settings.APP_ENV == "development":
        #     async with PostgresDatabase.engine.connect() as conn:
        #         result = await conn.execute(text("SELECT version_num FROM alembic_version"))
        #         version = result.scalar()
        #         if not version:
        #             log.error("No alembic version found in database")
        #             raise Exception("Database schema version verification failed")
        #         log.info(f"Current database schema version: {version}")
        await PostgresDatabase.init_db()
        yield
    finally:
        await PostgresDatabase.close_db()


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="AI Assistant API",
        version="1.0.0",
        description="AI Assistant API Documentation",
        routes=app.routes,
    )

    return openapi_schema


app = FastAPI(
    title="AI Assistant BE API",
    description="AI Assistant BE API Documentation",
    version="1.0.0",
    lifespan=lifespan,
)

app.openapi = custom_openapi


@app.middleware("http")
async def db_session_middleware(request, call_next):
    try:
        if not await PostgresDatabase.check_connection():
            await PostgresDatabase.connect_db()
        response = await call_next(request)
        return response
    except Exception as e:
        log.error(f"Middleware error: {str(e)}")
        raise e


app.include_router(health_router)
app.include_router(user_router)
app.include_router(task_router)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
