from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from src.config import Config

# Motor y sesión asíncronos exclusivos para el contexto IdP (cuando se usa Turso/SQLite local)
engine = create_async_engine(Config.IDP_DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

async def init_idp_db():
    """Inicializa las tablas del módulo IdP."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
