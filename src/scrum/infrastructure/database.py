from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from src.config import Config

# Motor y sesión asíncronos exclusivos para el contexto Scrum
engine = create_async_engine(Config.TURSO_DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

async def init_scrum_db():
    """Inicializa las tablas del módulo Scrum."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
