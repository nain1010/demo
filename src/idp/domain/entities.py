import uuid
from typing import Optional
from src.idp.domain.value_objects import GlobalRole

class User:
    def __init__(
        self,
        id: uuid.UUID,
        nombre_completo: str,
        email: str,
        rol_global: GlobalRole = GlobalRole.MIEMBRO,
        avatar_url: Optional[str] = None
    ):
        self.id = id
        self.nombre_completo = nombre_completo
        self.email = email
        self.rol_global = rol_global
        self.avatar_url = avatar_url


class Session:
    def __init__(
        self,
        token: str,
        usuario_id: uuid.UUID,
        is_active: bool = True
    ):
        self.token = token
        self.usuario_id = usuario_id
        self.is_active = is_active
