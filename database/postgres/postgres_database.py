import asyncio
import logging as log
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import backoff
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (AsyncEngine, AsyncSession,
                                    async_sessionmaker, create_async_engine)

from core.config import settings
from database.postgres.models.base import Base


class PostgresDatabase:
    engine: Optional[AsyncEngine] = None
    session_maker: Optional[async_sessionmaker] = None
    _ping_task: Optional[asyncio.Task] = None
    _connection_retries = 0
    MAX_RETRIES = 3

    @classmethod
    async def _keep_alive(cls) -> None:
        """Periodically ping the database to keep the connection alive"""
        while True:
            try:
                async with cls.engine.connect() as conn:
                    await conn.execute(text("SELECT 1"))
                    log.debug("PostgreSQL ping successful")
                await asyncio.sleep(settings.PING_INTERVAL)
            except Exception as e:
                log.error(f"PostgreSQL ping failed: {str(e)}")
                try:
                    await cls.connect_db()
                except Exception as reconnect_error:
                    log.error(f"PostgreSQL reconnection failed: {str(reconnect_error)}")
                await asyncio.sleep(5)  # Wait before retrying

    @classmethod
    async def start_keep_alive(cls) -> None:
        """Start the keep-alive mechanism"""
        if cls._ping_task is None or cls._ping_task.done():
            cls._ping_task = asyncio.create_task(cls._keep_alive())
            log.info("PostgreSQL keep-alive mechanism started")

    @classmethod
    async def stop_keep_alive(cls) -> None:
        """Stop the keep-alive mechanism"""
        if cls._ping_task and not cls._ping_task.done():
            cls._ping_task.cancel()
            try:
                await cls._ping_task
            except asyncio.CancelledError:
                pass
            cls._ping_task = None
            log.info("PostgreSQL keep-alive mechanism stopped")

    @classmethod
    @backoff.on_exception(
        backoff.expo, (SQLAlchemyError, asyncio.TimeoutError), max_tries=3, max_time=30
    )
    async def connect_db(cls) -> None:
        """Establish database connection with retry mechanism"""
        try:
            cls.engine = create_async_engine(
                settings.POSTGRES_DB_URL,
                echo=settings.DB_ECHO_LOG,
                pool_size=settings.PG_POOL_SIZE,
                max_overflow=settings.PG_MAX_OVERFLOW,
                pool_timeout=settings.PG_POOL_TIMEOUT,
                pool_recycle=settings.PG_POOL_RECYCLE,
                pool_pre_ping=True,
            )
            cls.session_maker = async_sessionmaker(
                cls.engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )

            # Test the connection
            async with cls.engine.connect() as conn:
                await conn.execute(text("SELECT 1"))

            log.info("Successfully connected to PostgreSQL")
            await cls.start_keep_alive()

        except Exception as e:
            log.error(f"Failed to connect to PostgreSQL: {str(e)}")
            raise SQLAlchemyError(f"Database connection failed: {str(e)}")

    @classmethod
    async def close_db(cls) -> None:
        """Safely close database connection"""
        try:
            await cls.stop_keep_alive()
            if cls.engine:
                await cls.engine.dispose()
                log.info("PostgreSQL connection closed")
        except Exception as e:
            log.error(f"Error closing PostgreSQL connection: {str(e)}")

    @classmethod
    async def check_connection(cls) -> bool:
        """Check if database connection is alive"""
        try:
            if cls.engine:
                async with cls.engine.connect() as conn:
                    await conn.execute(text("SELECT 1"))
                return True
            return False
        except Exception:
            return False

    @classmethod
    @asynccontextmanager
    async def get_session(cls) -> AsyncGenerator[AsyncSession, None]:
        """Get a database session with automatic cleanup"""
        if not cls.session_maker:
            await cls.connect_db()

        session = cls.session_maker()
        try:
            yield session
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

    @classmethod
    async def init_db(cls) -> None:
        try:
            log.info(f"Attempting to create tables: {Base.metadata.tables.keys()}")
            async with cls.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            log.info("Database initialized successfully")
        except Exception as e:
            log.error(f"Failed to initialize database: {str(e)}")
            raise e

    @classmethod
    async def run_migrations(cls) -> None:
        """Run database migrations using Alembic"""
        try:
            import asyncio

            from alembic import command
            from alembic.config import Config

            # Create Alembic configuration
            alembic_cfg = Config("alembic.ini")

            # Run migrations asynchronously
            def run_upgrade() -> None:
                command.upgrade(alembic_cfg, "head")

            await asyncio.get_event_loop().run_in_executor(None, run_upgrade)
            log.info("Database migrations completed successfully")
        except Exception as e:
            log.error(f"Failed to run database migrations: {str(e)}")
            raise e
