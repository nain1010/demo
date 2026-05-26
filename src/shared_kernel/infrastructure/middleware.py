from litestar.middleware import AbstractMiddleware
from litestar.types import ASGIApp, Receive, Scope, Send
from src.config import Config
from src.dependencies import provide_idp_session, provide_identity_service

class AuthMiddleware(AbstractMiddleware):
    """Middleware de autenticación ASGI para interceptar tokens y poblar el usuario en el request state."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # Asegurarse de tener el diccionario state
        if "state" not in scope:
            scope["state"] = {}
        scope["state"]["user"] = None

        # Leer headers (son bytes en ASGI)
        headers = dict(scope.get("headers", []))
        auth_bytes = headers.get(b"authorization", b"")
        auth_header = auth_bytes.decode("utf-8") if auth_bytes else ""

        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                if Config.AUTH_PROVIDER == "supabase":
                    # Supabase es stateless, no requiere sesión de BD
                    service = await provide_identity_service(None)
                    user = await service.validate_session(token)
                    scope["state"]["user"] = user
                else:
                    # Turso requiere una sesión temporal para consultar la BD local
                    async for session in provide_idp_session():
                        service = await provide_identity_service(session)
                        user = await service.validate_session(token)
                        scope["state"]["user"] = user
                        break
            except Exception:
                # Si falla la validación por cualquier motivo, se mantiene como None
                pass

        await self.app(scope, receive, send)
