from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from config import DATABASE_URL

from models.models import Base

engine = create_async_engine(DATABASE_URL, echo=True)  # echo=True → лог SQL

AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
