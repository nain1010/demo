import asyncio
import logging
from typing import Dict, Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from litestar import Litestar, get, Request, Response
from litestar.di import Provide
from litestar.exceptions import HTTPException
from litestar.status_codes import HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED, HTTP_404_NOT_FOUND, HTTP_503_SERVICE_UNAVAILABLE

from src.config import Config
from src.dependencies import dependencies
from src.idp.infrastructure.plugin import IdpPlugin
from src.scrum.infrastructure.plugin import ScrumPlugin
from src.shared_kernel.infrastructure.middleware import AuthMiddleware
from src.shared_kernel.infrastructure.outbox_processor import outbox_processor_loop
from src.shared_kernel.domain.exceptions import (
    DomainException,
    EntityNotFoundException,
    BusinessRuleValidationException,
    UnauthorizedException
)
from src.idp.infrastructure.database import init_idp_db
from src.scrum.infrastructure.database import init_scrum_db

# Configurar logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

# --- EXCEPTION HANDLERS ---

def domain_exception_handler(request: Request, exc: DomainException) -> Response:
    """Mapea excepciones del dominio a respuestas HTTP con códigos de estado semánticos."""
    status_code = HTTP_400_BAD_REQUEST
    error_type = exc.__class__.__name__

    if isinstance(exc, EntityNotFoundException):
        status_code = HTTP_404_NOT_FOUND
    elif isinstance(exc, BusinessRuleValidationException):
        status_code = HTTP_400_BAD_REQUEST
    elif isinstance(exc, UnauthorizedException):
        status_code = HTTP_401_UNAUTHORIZED

    return Response(
        content={
            "error": exc.message,
            "type": error_type,
            "status_code": status_code
        },
        status_code=status_code
    )


# --- HEALTH CHECK ENDPOINT ---

@get("/health")
async def health_check(
    scrum_session: AsyncSession,
    idp_session: AsyncSession
) -> Response[Dict[str, Any]]:
    """Endpoint de diagnóstico de salud del backend y sus conexiones de persistencia."""
    status = {
        "status": "healthy",
        "database_scrum": "unknown",
        "auth_provider": Config.AUTH_PROVIDER,
        "database_idp": "unknown"
    }
    is_healthy = True

    # 1. Comprobar base de datos de Scrum (Turso/SQLite)
    try:
        await scrum_session.execute(text("SELECT 1"))
        status["database_scrum"] = "connected"
    except Exception as e:
        status["database_scrum"] = f"error: {str(e)}"
        is_healthy = False

    # 2. Comprobar IdP
    if Config.AUTH_PROVIDER == "turso":
        try:
            await idp_session.execute(text("SELECT 1"))
            status["database_idp"] = "connected"
        except Exception as e:
            status["database_idp"] = f"error: {str(e)}"
            is_healthy = False
    elif Config.AUTH_PROVIDER == "supabase":
        try:
            # Ping ligero al endpoint de salud de Supabase Auth
            health_url = f"{Config.SUPABASE_URL.rstrip('/')}/auth/v1/health"
            headers = {"apikey": Config.SUPABASE_KEY}
            async with httpx.AsyncClient() as client:
                resp = await client.get(health_url, headers=headers, timeout=2.0)
                if resp.status_code == 200:
                    status["database_idp"] = "connected (supabase cloud)"
                else:
                    status["database_idp"] = f"error: status code {resp.status_code}"
                    is_healthy = False
        except Exception as e:
            status["database_idp"] = f"error: {str(e)}"
            is_healthy = False

    if not is_healthy:
        status["status"] = "unhealthy"
        return Response(content=status, status_code=HTTP_503_SERVICE_UNAVAILABLE)

    return Response(content=status)


# --- LIFECYCLE HOOKS ---

async def on_startup(app: Litestar) -> None:
    """Acciones a ejecutar al iniciar la aplicación Litestar."""
    # Validar configuraciones
    Config.validate()

    # Inicializar bases de datos locales si usamos SQLite
    if Config.AUTH_PROVIDER == "turso":
        logger.info("Inicializando bases de datos SQLite locales (IdP y Scrum)...")
        await init_idp_db()
    
    await init_scrum_db()

    # Arrancar la tarea en segundo plano para el Transactional Outbox
    if Config.AUTH_PROVIDER == "turso":
        asyncio.create_task(outbox_processor_loop(app))


# --- APPLICATION CONFIGURATION ---

app = Litestar(
    route_handlers=[health_check],
    plugins=[IdpPlugin(), ScrumPlugin()],
    middleware=[AuthMiddleware],
    dependencies=dependencies,
    exception_handlers={
        DomainException: domain_exception_handler,  # type: ignore
    },
    on_startup=[on_startup]
)
