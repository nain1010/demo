import uuid
from litestar import Controller, post, put, Request
from litestar.di import Provide
from pydantic import BaseModel
from src.idp.domain.ports import IdentityServicePort
from src.idp.domain.value_objects import GlobalRole
from src.shared_kernel.infrastructure.guards import guard_authenticated, guard_admin

class RegisterDTO(BaseModel):
    email: str
    password: str
    nombre_completo: str
    rol_global: GlobalRole


class LoginDTO(BaseModel):
    email: str
    password: str


class UpdateRoleDTO(BaseModel):
    rol_global: GlobalRole


class AuthController(Controller):
    path = ""

    @post("/register")
    async def register(self, data: RegisterDTO, identity_service: IdentityServicePort) -> dict:
        """Endpoint público para registrar nuevos usuarios en la plataforma."""
        user = await identity_service.register_user(
            email=data.email,
            password=data.password,
            nombre_completo=data.nombre_completo,
            rol_global=data.rol_global
        )
        return {
            "id": str(user.id),
            "nombre_completo": user.nombre_completo,
            "email": user.email,
            "rol_global": user.rol_global.value
        }

    @post("/login")
    async def login(self, data: LoginDTO, identity_service: IdentityServicePort) -> dict:
        """Endpoint público para iniciar sesión y obtener un token."""
        session = await identity_service.authenticate(email=data.email, password=data.password)
        return {
            "token": session.token,
            "usuario_id": str(session.usuario_id)
        }

    @put("/users/{user_id:uuid}/role", guards=[guard_admin])
    async def update_role(
        self,
        user_id: uuid.UUID,
        data: UpdateRoleDTO,
        identity_service: IdentityServicePort
    ) -> dict:
        """Endpoint protegido (Admin) para actualizar el rol global de un usuario."""
        user = await identity_service.update_user_role(user_id=user_id, nuevo_rol=data.rol_global)
        return {
            "id": str(user.id),
            "nombre_completo": user.nombre_completo,
            "rol_global": user.rol_global.value
        }
