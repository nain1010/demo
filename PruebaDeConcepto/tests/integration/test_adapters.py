import pytest
import uuid
import os
from datetime import date
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select

# Los motores de bases de datos se configuran de forma global en conftest.py

from src.scrum.infrastructure.database import Base as ScrumBase, engine as scrum_engine, init_scrum_db
from src.idp.infrastructure.database import Base as IdpBase, engine as idp_engine, init_idp_db
from src.scrum.infrastructure.adapters.sqlite_repository import SqliteScrumRepository
from src.idp.infrastructure.adapters.turso_adapter import TursoIdentityAdapter
from src.scrum.domain.aggregates import Proyecto
from src.scrum.domain.entities import Sprint, HistoriaUsuario, Tarea
from src.scrum.domain.value_objects import ScrumRole, SprintState, StoryState, TaskState
from src.shared_kernel.domain.value_objects import DateRange
from src.idp.domain.value_objects import GlobalRole
from src.idp.infrastructure.models import UserModel, OutboxEventModel

import pytest_asyncio

from pathlib import Path

# Fixture de sesión para Scrum
@pytest_asyncio.fixture
async def scrum_session():
    # Eliminar archivo si existe
    path = Path("scrum_test.db")
    if path.exists():
        try:
            path.unlink()
        except Exception:
            pass

    # Inicializar tablas
    await init_scrum_db()
    SessionMaker = async_sessionmaker(bind=scrum_engine, class_=AsyncSession, expire_on_commit=False)
    async with SessionMaker() as session:
        yield session
    # Cerrar conexiones
    await scrum_engine.dispose()
    
    if path.exists():
        try:
            path.unlink()
        except Exception:
            pass

# Fixture de sesión para IdP
@pytest_asyncio.fixture
async def idp_session():
    # Eliminar archivo si existe
    path = Path("idp_test.db")
    if path.exists():
        try:
            path.unlink()
        except Exception:
            pass

    # Inicializar tablas
    await init_idp_db()
    SessionMaker = async_sessionmaker(bind=idp_engine, class_=AsyncSession, expire_on_commit=False)
    async with SessionMaker() as session:
        yield session
    # Cerrar conexiones
    await idp_engine.dispose()

    if path.exists():
        try:
            path.unlink()
        except Exception:
            pass

@pytest.mark.asyncio
async def test_scrum_repository_save_and_get(scrum_session):
    repo = SqliteScrumRepository(scrum_session)
    
    # Crear agregado Proyecto
    proj_id = uuid.uuid4()
    proyecto = Proyecto(
        id=proj_id,
        nombre="Proyecto Integración",
        descripcion="Test de base de datos",
        fecha_inicio=date(2026, 6, 1)
    )
    
    # Asignar roles
    po_id = uuid.uuid4()
    sm_id = uuid.uuid4()
    dev_id = uuid.uuid4()
    proyecto.asignar_rol(po_id, ScrumRole.PRODUCT_OWNER)
    proyecto.asignar_rol(sm_id, ScrumRole.SCRUM_MASTER)
    proyecto.asignar_rol(dev_id, ScrumRole.DEVELOPER)
    
    # Agregar Sprint
    sprint_id = uuid.uuid4()
    sprint = Sprint(
        id=sprint_id,
        nombre="Sprint 1",
        rango_fechas=DateRange(date(2026, 6, 1), date(2026, 6, 15)),
        objetivo="Objetivo de integración"
    )
    proyecto.agregar_sprint(sprint)
    
    # Crear e Instanciar Historia
    h_id = uuid.uuid4()
    historia = HistoriaUsuario(
        id=h_id,
        correlativo="US-100",
        titulo="Historia de integración",
        narrativa="Como test...",
        criterios_aceptacion=["Debe pasar"]
    )
    proyecto.crear_historia_usuario(historia, ejecutado_por=po_id)
    proyecto.estimar_historia(h_id, 8, ejecutado_por=dev_id)
    proyecto.asociar_historia_a_sprint(h_id, sprint_id, ejecutado_por=po_id)
    
    # Crear tarea
    t_id = uuid.uuid4()
    tarea = Tarea(
        id=t_id,
        titulo="Tarea de integración",
        descripcion="Implementar tests"
    )
    proyecto.crear_tarea_en_historia(h_id, tarea, ejecutado_por=dev_id)
    proyecto.cambiar_estado_tarea(t_id, TaskState.EN_CURSO, ejecutado_por=dev_id)
    
    # Guardar en base de datos
    await repo.save(proyecto)
    await scrum_session.commit()
    
    # Recuperar de base de datos en una nueva sesión o limpiando la actual
    scrum_session.expire_all()
    proyecto_recuperado = await repo.get_by_id(proj_id)
    
    # Validaciones del agregado reconstruido
    assert proyecto_recuperado is not None
    assert proyecto_recuperado.nombre == "Proyecto Integración"
    assert proyecto_recuperado.fecha_inicio == date(2026, 6, 1)
    
    # Roles
    assert proyecto_recuperado.memberships[po_id] == ScrumRole.PRODUCT_OWNER
    assert proyecto_recuperado.memberships[sm_id] == ScrumRole.SCRUM_MASTER
    assert proyecto_recuperado.memberships[dev_id] == ScrumRole.DEVELOPER
    
    # Sprints
    assert len(proyecto_recuperado.sprints) == 1
    assert proyecto_recuperado.sprints[0].nombre == "Sprint 1"
    assert proyecto_recuperado.sprints[0].rango_fechas.duration_days == 14
    
    # Historias
    assert len(proyecto_recuperado.historias_usuario) == 1
    assert proyecto_recuperado.historias_usuario[0].correlativo == "US-100"
    assert proyecto_recuperado.historias_usuario[0].esfuerzo_estimado == 8
    assert proyecto_recuperado.historias_usuario[0].estado == StoryState.EN_PROGRESO # Sincronizado por la tarea en curso
    
    # Tareas
    assert len(proyecto_recuperado.tareas) == 1
    assert proyecto_recuperado.tareas[0].titulo == "Tarea de integración"
    assert proyecto_recuperado.tareas[0].estado == TaskState.EN_CURSO

@pytest.mark.asyncio
async def test_turso_identity_adapter_integration(idp_session):
    adapter = TursoIdentityAdapter(idp_session)
    
    # Registrar usuario
    user = await adapter.register_user(
        email="test_integration@test.com",
        password="secure123password",
        nombre_completo="Integration User",
        rol_global=GlobalRole.MIEMBRO
    )
    
    assert user.email == "test_integration@test.com"
    assert user.rol_global == GlobalRole.MIEMBRO
    
    # Verificar que el evento se insertó en la outbox de forma atómica
    res_outbox = await idp_session.execute(select(OutboxEventModel))
    events = res_outbox.scalars().all()
    assert len(events) == 1
    assert events[0].event_name == "UserRegistered"
    assert events[0].payload["email"] == "test_integration@test.com"
    assert events[0].processed is False
    
    # Autenticar
    session = await adapter.authenticate("test_integration@test.com", "secure123password")
    assert session.is_active is True
    
    # Validar sesión
    validated_user = await adapter.validate_session(session.token)
    assert validated_user is not None
    assert validated_user.id == user.id
    
    # Actualizar Rol y verificar nuevo evento outbox
    await adapter.update_user_role(user.id, GlobalRole.ADMINISTRADOR)
    
    res_outbox2 = await idp_session.execute(select(OutboxEventModel).where(OutboxEventModel.event_name == "UserRoleUpdated"))
    role_event = res_outbox2.scalar_one_or_none()
    assert role_event is not None
    assert role_event.payload["rol_global"] == GlobalRole.ADMINISTRADOR.value
    assert role_event.processed is False
