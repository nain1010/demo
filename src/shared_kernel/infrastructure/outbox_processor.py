import asyncio
import logging
import uuid
from sqlalchemy import select
from src.config import Config
from src.dependencies import provide_idp_session, provide_scrum_session
from src.idp.infrastructure.models import OutboxEventModel
from src.scrum.application.integration_service import ScrumIntegrationService

logger = logging.getLogger("outbox_processor")

async def process_outbox_events():
    """Busca eventos pendientes en el Outbox del IdP y los despacha al módulo Scrum."""
    if Config.AUTH_PROVIDER == "supabase":
        # Supabase maneja su propio estado en la nube, no usamos outbox local en este modo
        return

    # 1. Obtener sesión de base de datos del IdP
    async for idp_session in provide_idp_session():
        # Consultar eventos no procesados
        res = await idp_session.execute(
            select(OutboxEventModel)
            .where(OutboxEventModel.processed == False)
            .order_by(OutboxEventModel.occurred_on)
        )
        events = res.scalars().all()
        if not events:
            return

        # 2. Obtener sesión de base de datos de Scrum para sincronizar
        async for scrum_session in provide_scrum_session():
            scrum_integration = ScrumIntegrationService(scrum_session)
            
            for event in events:
                try:
                    logger.info(f"Procesando evento Outbox {event.event_name} (ID: {event.event_id})")
                    payload = event.payload
                    
                    if event.event_name == "UserRegistered":
                        await scrum_integration.handle_user_registered(
                            user_id=uuid.UUID(payload["id"]),
                            nombre_completo=payload["nombre_completo"],
                            email=payload["email"],
                            rol_global=payload["rol_global"]
                        )
                    elif event.event_name == "UserRoleUpdated":
                        await scrum_integration.handle_user_role_updated(
                            user_id=uuid.UUID(payload["id"]),
                            nuevo_rol=payload["rol_global"]
                        )
                    
                    # Marcar como procesado si se despachó con éxito
                    event.processed = True
                    await idp_session.commit()
                    logger.info(f"Evento {event.event_id} marcado como procesado.")
                    
                except Exception as e:
                    logger.error(f"Fallo al procesar evento Outbox {event.event_id}: {e}")
                    await idp_session.rollback()
                    await scrum_session.rollback()
                    # Salir para reintentar en la próxima iteración del loop
                    return
            break
        break


async def outbox_processor_loop(app):
    """Loop infinito que se ejecuta en segundo plano en Litestar."""
    logger.info("Iniciando tarea en segundo plano: Outbox Processor Loop...")
    while True:
        try:
            await process_outbox_events()
        except Exception as e:
            logger.error(f"Error crítico en el loop de procesamiento de Outbox: {e}")
        # Esperar 5 segundos antes de volver a consultar
        await asyncio.sleep(5)
