from sqlalchemy.ext.asyncio import AsyncSession
from litestar.di import Provide
from src.config import Config

from src.idp.domain.ports import IdentityServicePort
from src.idp.infrastructure.database import SessionLocal as IdpSessionLocal
from src.idp.infrastructure.adapters.turso_adapter import TursoIdentityAdapter
from src.idp.infrastructure.adapters.supabase_adapter import SupabaseIdentityAdapter

from src.scrum.domain.ports import ScrumRepositoryPort
from src.scrum.infrastructure.database import SessionLocal as ScrumSessionLocal
from src.scrum.infrastructure.adapters.sqlite_repository import SqliteScrumRepository

# --- IDP DEPENDENCIES ---

async def provide_idp_session() -> AsyncSession:
    """Proveedor asíncrono de sesión para la base de datos de identidad (IdP)."""
    async with IdpSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def provide_identity_service(idp_session: AsyncSession) -> IdentityServicePort:
    """Proveedor dinámico de IdentityServicePort según configuración."""
    if Config.AUTH_PROVIDER == "supabase":
        return SupabaseIdentityAdapter(
            supabase_url=Config.SUPABASE_URL,
            supabase_key=Config.SUPABASE_KEY
        )
    else:
        return TursoIdentityAdapter(session=idp_session)


# --- SCRUM DEPENDENCIES ---

async def provide_scrum_session() -> AsyncSession:
    """Proveedor asíncrono de sesión para la base de datos Scrum."""
    async with ScrumSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def provide_scrum_repository(scrum_session: AsyncSession) -> ScrumRepositoryPort:
    """Proveedor del puerto de repositorio Scrum."""
    return SqliteScrumRepository(session=scrum_session)


# Dependencias globales listas para registrar en Litestar
dependencies = {
    "idp_session": Provide(provide_idp_session),
    "identity_service": Provide(provide_identity_service),
    "scrum_session": Provide(provide_scrum_session),
    "scrum_repository": Provide(provide_scrum_repository)
}
