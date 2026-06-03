import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.scrum.infrastructure.models import UsuarioScrumModel

class ScrumIntegrationService:
    """Servicio de aplicación en el contexto Scrum para procesar eventos provenientes de otros contextos (IdP)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def handle_user_registered(self, user_id: uuid.UUID, nombre_completo: str, email: str, rol_global: str):
        """Manejador del evento de registro de usuario: guarda una réplica local para aislamiento."""
        user = UsuarioScrumModel(
            id=str(user_id),
            nombre_completo=nombre_completo,
            email=email,
            rol_global=rol_global
        )
        self.session.add(user)
        await self.session.commit()

    async def handle_user_role_updated(self, user_id: uuid.UUID, nuevo_rol: str):
        """Manejador del evento de cambio de rol de usuario: sincroniza el rol localmente."""
        res = await self.session.execute(
            select(UsuarioScrumModel).where(UsuarioScrumModel.id == str(user_id))
        )
        user = res.scalar_one_or_none()
        if user:
            user.rol_global = nuevo_rol
            await self.session.commit()
