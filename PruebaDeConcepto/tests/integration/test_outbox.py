import pytest
import uuid
import os
from sqlalchemy import select
from pathlib import Path

# Variables de entorno de prueba configuradas globalmente en conftest.py

from src.scrum.infrastructure.database import Base as ScrumBase, engine as scrum_engine, init_scrum_db
from src.idp.infrastructure.database import Base as IdpBase, engine as idp_engine, init_idp_db
from src.idp.infrastructure.adapters.turso_adapter import TursoIdentityAdapter
from src.shared_kernel.infrastructure.outbox_processor import process_outbox_events
from src.scrum.infrastructure.models import UsuarioScrumModel
from src.idp.infrastructure.models import OutboxEventModel
from src.idp.domain.value_objects import GlobalRole
from src.config import Config
from src.dependencies import provide_idp_session, provide_scrum_session

import pytest_asyncio

@pytest_asyncio.fixture
async def setup_databases():
    # Eliminar archivos anteriores si existen
    for db_file in ["scrum_test.db", "idp_test.db"]:
        path = Path(db_file)
        if path.exists():
            try:
                path.unlink()
            except Exception:
                pass

    # Inicializar ambas bases de datos
    await init_scrum_db()
    await init_idp_db()
    
    yield
    
    # Cerrar conexiones para poder borrar los archivos
    await scrum_engine.dispose()
    await idp_engine.dispose()

    # Eliminar archivos al finalizar
    for db_file in ["scrum_test.db", "idp_test.db"]:
        path = Path(db_file)
        if path.exists():
            try:
                path.unlink()
            except Exception:
                pass

@pytest.mark.asyncio
async def test_outbox_eventual_consistency_flow(setup_databases):
    # Asegurar que el proveedor está configurado como turso para procesar el outbox
    Config.AUTH_PROVIDER = "turso"
    
    # 1. Registrar un usuario mediante el adaptador de Turso (IdP)
    async for idp_session in provide_idp_session():
        adapter = TursoIdentityAdapter(idp_session)
        user = await adapter.register_user(
            email="outbox@test.com",
            password="pwd",
            nombre_completo="Outbox User",
            rol_global=GlobalRole.MIEMBRO
        )
        break
    
    # 2. Verificar que el evento está en la outbox de IdP como no procesado
    async for idp_session in provide_idp_session():
        res = await idp_session.execute(select(OutboxEventModel))
        event = res.scalar_one_or_none()
        assert event is not None
        assert event.event_name == "UserRegistered"
        assert event.processed is False
        break
        
    # 3. Ejecutar el procesador del Outbox
    await process_outbox_events()
    
    # 4. Verificar que el evento se marcó como procesado
    async for idp_session in provide_idp_session():
        res = await idp_session.execute(select(OutboxEventModel))
        event = res.scalar_one_or_none()
        assert event is not None
        assert event.processed is True
        break
        
    # 5. Verificar que el usuario se replicó en la tabla de Scrum
    async for scrum_session in provide_scrum_session():
        res = await scrum_session.execute(select(UsuarioScrumModel).where(UsuarioScrumModel.id == str(user.id)))
        replicated_user = res.scalar_one_or_none()
        assert replicated_user is not None
        assert replicated_user.nombre_completo == "Outbox User"
        assert replicated_user.email == "outbox@test.com"
        assert replicated_user.rol_global == GlobalRole.MIEMBRO.value
        break
