import uuid
import hashlib
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.idp.domain.entities import User, Session
from src.idp.domain.value_objects import GlobalRole
from src.idp.domain.ports import IdentityServicePort
from src.idp.infrastructure.models import UserModel, SessionModel, OutboxEventModel
from src.shared_kernel.domain.exceptions import (
    BusinessRuleValidationException,
    EntityNotFoundException,
    UnauthorizedException
)

class TursoIdentityAdapter(IdentityServicePort):
    """Adaptador de identidad para Turso (SQLite local/distribuida) con Transactional Outbox."""

    def __init__(self, session: AsyncSession):
        self.session = session

    def _hash_password(self, password: str) -> str:
        """Genera un hash SHA256 seguro para las contraseñas."""
        return hashlib.sha256(password.encode()).hexdigest()

    async def _add_to_outbox(self, event_name: str, payload: dict):
        """Helper para insertar un evento en la tabla Outbox dentro de la misma transacción."""
        outbox_event = OutboxEventModel(
            event_id=str(uuid.uuid4()),
            event_name=event_name,
            payload=payload,
            occurred_on=datetime.now(timezone.utc),
            processed=False
        )
        self.session.add(outbox_event)

    async def register_user(self, email: str, password: str, nombre_completo: str, rol_global: GlobalRole) -> User:
        # Verificar duplicado
        res = await self.session.execute(select(UserModel).where(UserModel.email == email))
        if res.scalar_one_or_none():
            raise BusinessRuleValidationException("El correo electrónico ya está registrado.")

        user_id = uuid.uuid4()
        user_model = UserModel(
            id=str(user_id),
            nombre_completo=nombre_completo,
            email=email,
            rol_global=rol_global.value,
            password_hash=self._hash_password(password),
            avatar_url=None
        )
        self.session.add(user_model)

        # Transactional Outbox: Publicar evento de registro
        await self.session.flush() # Asegura ID e integridad antes del evento
        await self._add_to_outbox(
            event_name="UserRegistered",
            payload={
                "id": str(user_id),
                "nombre_completo": nombre_completo,
                "email": email,
                "rol_global": rol_global.value
            }
        )
        
        await self.session.commit()

        return User(
            id=user_id,
            nombre_completo=nombre_completo,
            email=email,
            rol_global=rol_global
        )

    async def authenticate(self, email: str, password: str) -> Session:
        hashed = self._hash_password(password)
        res = await self.session.execute(
            select(UserModel).where((UserModel.email == email) & (UserModel.password_hash == hashed))
        )
        user_model = res.scalar_one_or_none()
        if not user_model:
            raise UnauthorizedException("Credenciales inválidas.")

        token = f"session-token-{uuid.uuid4()}"
        session_model = SessionModel(
            token=token,
            usuario_id=user_model.id,
            is_active=True
        )
        self.session.add(session_model)
        await self.session.commit()

        return Session(
            token=token,
            usuario_id=uuid.UUID(user_model.id),
            is_active=True
        )

    async def get_user_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        res = await self.session.execute(select(UserModel).where(UserModel.id == str(user_id)))
        user_model = res.scalar_one_or_none()
        if not user_model:
            return None
        return User(
            id=uuid.UUID(user_model.id),
            nombre_completo=user_model.nombre_completo,
            email=user_model.email,
            rol_global=GlobalRole(user_model.rol_global),
            avatar_url=user_model.avatar_url
        )

    async def validate_session(self, token: str) -> Optional[User]:
        res_sess = await self.session.execute(
            select(SessionModel).where((SessionModel.token == token) & (SessionModel.is_active == True))
        )
        session_model = res_sess.scalar_one_or_none()
        if not session_model:
            return None

        return await self.get_user_by_id(uuid.UUID(session_model.usuario_id))

    async def update_user_role(self, user_id: uuid.UUID, nuevo_rol: GlobalRole) -> User:
        res = await self.session.execute(select(UserModel).where(UserModel.id == str(user_id)))
        user_model = res.scalar_one_or_none()
        if not user_model:
            raise EntityNotFoundException("Usuario no encontrado.")

        user_model.rol_global = nuevo_rol.value
        
        # Transactional Outbox: Evento de cambio de rol
        await self._add_to_outbox(
            event_name="UserRoleUpdated",
            payload={
                "id": str(user_id),
                "rol_global": nuevo_rol.value
            }
        )
        
        await self.session.commit()

        return User(
            id=uuid.UUID(user_model.id),
            nombre_completo=user_model.nombre_completo,
            email=user_model.email,
            rol_global=nuevo_rol,
            avatar_url=user_model.avatar_url
        )
