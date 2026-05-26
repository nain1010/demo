import uuid
from typing import Optional, Dict, Tuple
from src.idp.domain.entities import User, Session
from src.idp.domain.value_objects import GlobalRole
from src.idp.domain.ports import IdentityServicePort
from src.shared_kernel.domain.exceptions import (
    BusinessRuleValidationException,
    EntityNotFoundException,
    UnauthorizedException
)

class InMemoryIdentityAdapter(IdentityServicePort):
    """Adaptador en memoria para simular el proveedor de identidad de forma rápida y local."""
    
    def __init__(self):
        self.users: Dict[uuid.UUID, User] = {}
        self.sessions: Dict[str, Session] = {}
        # Mapea email -> (password, user_id)
        self.credentials: Dict[str, Tuple[str, uuid.UUID]] = {}

    async def register_user(self, email: str, password: str, nombre_completo: str, rol_global: GlobalRole) -> User:
        if email in self.credentials:
            raise BusinessRuleValidationException("El correo electrónico ya está registrado.")
        
        user_id = uuid.uuid4()
        user = User(
            id=user_id,
            nombre_completo=nombre_completo,
            email=email,
            rol_global=rol_global
        )
        self.users[user_id] = user
        self.credentials[email] = (password, user_id)
        return user

    async def authenticate(self, email: str, password: str) -> Session:
        if email not in self.credentials or self.credentials[email][0] != password:
            raise UnauthorizedException("Credenciales inválidas.")
        
        user_id = self.credentials[email][1]
        token = f"mock-session-token-{uuid.uuid4()}"
        session = Session(token=token, usuario_id=user_id, is_active=True)
        self.sessions[token] = session
        return session

    async def get_user_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        return self.users.get(user_id)

    async def validate_session(self, token: str) -> Optional[User]:
        session = self.sessions.get(token)
        if session and session.is_active:
            return self.users.get(session.usuario_id)
        return None

    async def update_user_role(self, user_id: uuid.UUID, nuevo_rol: GlobalRole) -> User:
        user = self.users.get(user_id)
        if not user:
            raise EntityNotFoundException("Usuario no encontrado.")
        user.rol_global = nuevo_rol
        return user
