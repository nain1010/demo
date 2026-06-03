import uuid
from litestar.connection import ASGIConnection
from litestar.handlers.base import BaseRouteHandler
from litestar.exceptions import NotAuthorizedException, PermissionDeniedException

from src.idp.domain.value_objects import GlobalRole
from src.scrum.domain.value_objects import ScrumRole
from src.shared_kernel.domain.exceptions import EntityNotFoundException

def guard_authenticated(connection: ASGIConnection, _: BaseRouteHandler) -> None:
    """Valida que exista un usuario autenticado en la sesión."""
    user = connection.scope.get("state", {}).get("user")
    if not user:
        raise NotAuthorizedException("Debe estar autenticado para realizar esta acción.")


def guard_admin(connection: ASGIConnection, _: BaseRouteHandler) -> None:
    """Valida que el usuario sea Administrador global de la plataforma."""
    user = connection.scope.get("state", {}).get("user")
    if not user:
        raise NotAuthorizedException("Debe estar autenticado.")
    if user.rol_global != GlobalRole.ADMINISTRADOR:
        raise PermissionDeniedException("Acción exclusiva para administradores del sistema.")


def check_project_role(allowed_scrum_roles: list[ScrumRole]):
    """Guardia dinámico que valida si el usuario posee un rol permitido dentro de un proyecto Scrum."""
    
    async def guard(connection: ASGIConnection, _: BaseRouteHandler) -> None:
        user = connection.scope.get("state", {}).get("user")
        if not user:
            raise NotAuthorizedException("Debe estar autenticado.")

        # Extraer el project_id de los parámetros de ruta
        project_id_param = connection.path_params.get("project_id")
        if not project_id_param:
            raise PermissionDeniedException("Parámetro 'project_id' faltante en la ruta.")

        if isinstance(project_id_param, uuid.UUID):
            project_id = project_id_param
        else:
            try:
                project_id = uuid.UUID(project_id_param)
            except ValueError:
                raise PermissionDeniedException("El identificador del proyecto no es un UUID válido.")

        # Resolver el repositorio abriendo una sesión Scrum
        from src.dependencies import provide_scrum_session, provide_scrum_repository
        async for session in provide_scrum_session():
            repo = await provide_scrum_repository(session)
            proyecto = await repo.get_by_id(project_id)
            if not proyecto:
                # Arrojar 404
                raise PermissionDeniedException("Proyecto no encontrado.")
            
            # Verificar rol
            user_role = proyecto.memberships.get(user.id)
            if user_role not in allowed_scrum_roles:
                role_names = ", ".join([r.value for r in allowed_scrum_roles])
                current_role = user_role.value if user_role else "Ninguno"
                raise PermissionDeniedException(
                    f"Permisos insuficientes. Se requiere rol: {role_names}. Tu rol en el proyecto es: {current_role}"
                )
            break

    return guard
