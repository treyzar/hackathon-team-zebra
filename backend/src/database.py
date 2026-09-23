from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import settings

dbengine = create_async_engine(settings.db_url, echo=False, pool_pre_ping=True)
async_factory = async_sessionmaker(
    dbengine, expire_on_commit=False, class_=AsyncSession
)


async def access_db() -> AsyncIterator[AsyncSession]:
    async with async_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
