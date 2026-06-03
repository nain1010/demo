from abc import ABC, abstractmethod
import uuid
from typing import Optional
from src.idp.domain.entities import User, Session
from src.idp.domain.value_objects import GlobalRole

class IdentityServicePort(ABC):
    """Puerto (Interface) abstracto que define los servicios del IdP."""
    
    @abstractmethod
    async def register_user(self, email: str, password: str, nombre_completo: str, rol_global: GlobalRole) -> User:
        """Registra un nuevo usuario en la base de datos de identidad."""
        pass

    @abstractmethod
    async def authenticate(self, email: str, password: str) -> Session:
        """Autentica a un usuario y genera una sesión activa."""
        pass

    @abstractmethod
    async def get_user_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """Obtiene un usuario por su identificador único."""
        pass

    @abstractmethod
    async def validate_session(self, token: str) -> Optional[User]:
        """Valida si un token de sesión es activo y devuelve el usuario correspondiente."""
        pass

    @abstractmethod
    async def update_user_role(self, user_id: uuid.UUID, nuevo_rol: GlobalRole) -> User:
        """Actualiza el rol global del usuario (ej. cambiar a Administrador)."""
        pass
