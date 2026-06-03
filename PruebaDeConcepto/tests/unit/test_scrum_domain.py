import pytest
import uuid
from datetime import date
from src.shared_kernel.domain.exceptions import BusinessRuleValidationException
from src.shared_kernel.domain.value_objects import DateRange
from src.scrum.domain.value_objects import ScrumRole, SprintState, StoryState, TaskState
from src.scrum.domain.aggregates import Proyecto
from src.scrum.domain.entities import Sprint, HistoriaUsuario, Tarea

# Fixture base para crear usuarios
USER_ADMIN_ID = uuid.uuid4()
USER_PO_ID = uuid.uuid4()
USER_SM_ID = uuid.uuid4()
USER_DEV_ID = uuid.uuid4()
USER_DEV2_ID = uuid.uuid4()

def create_valid_project() -> Proyecto:
    """Crea un proyecto válido con los roles mínimos configurados (1 PO, 1 SM, 1 Dev)."""
    proyecto = Proyecto(
        id=uuid.uuid4(),
        nombre="Proyecto PoC",
        descripcion="Descripción de prueba",
        fecha_inicio=date(2026, 6, 1)
    )
    proyecto.asignar_rol(USER_PO_ID, ScrumRole.PRODUCT_OWNER)
    proyecto.asignar_rol(USER_SM_ID, ScrumRole.SCRUM_MASTER)
    proyecto.asignar_rol(USER_DEV_ID, ScrumRole.DEVELOPER)
    return proyecto

# --- PRUEBAS DE ROLES Y MEMBRESÍA ---

def test_proyecto_debe_tener_exactamente_un_po_y_un_sm_para_planificar_sprint():
    # Caso 1: Proyecto vacío (sin PO ni SM)
    proyecto_vacio = Proyecto(id=uuid.uuid4(), nombre="Proyecto Sin Roles", fecha_inicio=date(2026, 6, 1))
    sprint = Sprint(id=uuid.uuid4(), nombre="Sprint 1", rango_fechas=DateRange(date(2026, 6, 1), date(2026, 6, 15)))
    
    with pytest.raises(BusinessRuleValidationException) as exc:
        proyecto_vacio.agregar_sprint(sprint)
    assert "Debe contar con exactamente un Product Owner y un Scrum Master" in str(exc.value)

    # Caso 2: Solo tiene Scrum Master
    proyecto_vacio.asignar_rol(USER_SM_ID, ScrumRole.SCRUM_MASTER)
    with pytest.raises(BusinessRuleValidationException):
        proyecto_vacio.agregar_sprint(sprint)

    # Caso 3: Agregamos Product Owner (ahora debe funcionar)
    proyecto_vacio.asignar_rol(USER_PO_ID, ScrumRole.PRODUCT_OWNER)
    proyecto_vacio.agregar_sprint(sprint)  # No debería lanzar excepción

def test_proyecto_no_permite_multiples_po_o_sm():
    proyecto = create_valid_project()
    # Intentar asignar otro PO debería reemplazar o validar.
    # El requerimiento dice "exactamente un (1) Product Owner y un (1) Scrum Master designados".
    # Si asignamos otro, la asignación debe ser validada o lanzar error si intentamos tener más de uno activo.
    # Diseñemos `asignar_rol` de forma que valide que solo haya uno de cada uno:
    otro_usuario = uuid.uuid4()
    with pytest.raises(BusinessRuleValidationException) as exc:
        proyecto.asignar_rol(otro_usuario, ScrumRole.PRODUCT_OWNER)
    assert "Ya existe un Product Owner asignado a este proyecto" in str(exc.value)


# --- PRUEBAS DE ESTIMACIÓN DE ESFUERZO (FIBONACCI) ---

def test_estimacion_con_puntos_fibonacci_validos():
    proyecto = create_valid_project()
    historia = HistoriaUsuario(id=uuid.uuid4(), correlativo="US-001", titulo="Historia de prueba", narrativa="Como...", criterios_aceptacion=["Ok"])
    proyecto.crear_historia_usuario(historia, ejecutado_por=USER_PO_ID)
    
    # Estimaciones válidas: 0, 1, 2, 3, 5, 8, 13, 21
    for puntos in [0, 1, 2, 3, 5, 8, 13, 21]:
        proyecto.estimar_historia(historia.id, puntos, ejecutado_por=USER_DEV_ID)
        assert historia.esfuerzo_estimado == puntos

def test_estimacion_con_puntos_invalidos_falla():
    proyecto = create_valid_project()
    historia = HistoriaUsuario(id=uuid.uuid4(), correlativo="US-001", titulo="Historia de prueba", narrativa="Como...", criterios_aceptacion=["Ok"])
    proyecto.crear_historia_usuario(historia, ejecutado_por=USER_PO_ID)
    
    # 4 no es Fibonacci de Scrum
    with pytest.raises(BusinessRuleValidationException) as exc:
        proyecto.estimar_historia(historia.id, 4, ejecutado_por=USER_DEV_ID)
    assert "La estimación debe estar estrictamente en la escala Fibonacci de Scrum" in str(exc.value)


# --- PRUEBAS DEL CICLO DE VIDA DE SPRINT ---

def test_solo_un_sprint_puede_estar_activo_a_la_vez():
    proyecto = create_valid_project()
    
    sprint1 = Sprint(id=uuid.uuid4(), nombre="Sprint 1", rango_fechas=DateRange(date(2026, 6, 1), date(2026, 6, 15)))
    sprint2 = Sprint(id=uuid.uuid4(), nombre="Sprint 2", rango_fechas=DateRange(date(2026, 6, 16), date(2026, 6, 30)))
    
    proyecto.agregar_sprint(sprint1)
    proyecto.agregar_sprint(sprint2)
    
    # Activar el primer sprint
    proyecto.activar_sprint(sprint1.id, ejecutado_por=USER_SM_ID)
    assert sprint1.estado == SprintState.ACTIVO
    
    # Intentar activar el segundo sprint debe fallar
    with pytest.raises(BusinessRuleValidationException) as exc:
        proyecto.activar_sprint(sprint2.id, ejecutado_por=USER_SM_ID)
    assert "existe otro Sprint actualmente activo" in str(exc.value)

def test_no_se_pueden_agregar_historias_sin_estimar_a_sprint_activo():
    proyecto = create_valid_project()
    sprint = Sprint(id=uuid.uuid4(), nombre="Sprint 1", rango_fechas=DateRange(date(2026, 6, 1), date(2026, 6, 15)))
    proyecto.agregar_sprint(sprint)
    
    historia = HistoriaUsuario(id=uuid.uuid4(), correlativo="US-001", titulo="Historia 1", narrativa="Como...", criterios_aceptacion=["Ok"])
    proyecto.crear_historia_usuario(historia, ejecutado_por=USER_PO_ID)
    
    # Intentar comprometer historia sin estimación (esfuerzo = 0) a un sprint activo debería fallar, 
    # o si el sprint está en planificación se puede mover, pero no se puede ACTIVAR el sprint con historias sin estimar, 
    # o no se puede asociar una historia sin estimar a un sprint activo.
    # Validemos ambas restricciones:
    
    # 1. En planificación se puede mover (pasa a COMPROMETIDA)
    proyecto.asociar_historia_a_sprint(historia.id, sprint.id, ejecutado_por=USER_PO_ID)
    assert historia.estado == StoryState.COMPROMETIDA
    
    # 2. Al intentar ACTIVAR el sprint con una historia que tiene 0 puntos, debe fallar.
    with pytest.raises(BusinessRuleValidationException) as exc:
        proyecto.activar_sprint(sprint.id, ejecutado_por=USER_SM_ID)
    assert "no puede ingresar a un Sprint activo" in str(exc.value) or "contiene historias sin estimar" in str(exc.value).lower()

def test_bloqueo_de_fechas_al_activar_sprint():
    proyecto = create_valid_project()
    sprint = Sprint(id=uuid.uuid4(), nombre="Sprint 1", rango_fechas=DateRange(date(2026, 6, 1), date(2026, 6, 15)))
    proyecto.agregar_sprint(sprint)
    
    # Agregamos una historia estimada
    historia = HistoriaUsuario(id=uuid.uuid4(), correlativo="US-001", titulo="Historia 1", narrativa="Como...", criterios_aceptacion=["Ok"])
    proyecto.crear_historia_usuario(historia, ejecutado_por=USER_PO_ID)
    proyecto.estimar_historia(historia.id, 5, ejecutado_por=USER_DEV_ID)
    proyecto.asociar_historia_a_sprint(historia.id, sprint.id, ejecutado_por=USER_PO_ID)
    
    # Activar sprint
    proyecto.activar_sprint(sprint.id, ejecutado_por=USER_SM_ID)
    
    # Intentar cambiar fechas del sprint activo debe fallar
    with pytest.raises(BusinessRuleValidationException) as exc:
        sprint.actualizar_rango_fechas(DateRange(date(2026, 6, 2), date(2026, 6, 16)))
    assert "rango de fechas queda bloqueado" in str(exc.value)

def test_velocidad_comprometida_y_cierre_de_sprint():
    proyecto = create_valid_project()
    sprint = Sprint(id=uuid.uuid4(), nombre="Sprint 1", rango_fechas=DateRange(date(2026, 6, 1), date(2026, 6, 15)))
    proyecto.agregar_sprint(sprint)
    
    # Historia 1 (5 puntos)
    h1 = HistoriaUsuario(id=uuid.uuid4(), correlativo="US-001", titulo="Historia 1", narrativa="Como...", criterios_aceptacion=["Ok"])
    proyecto.crear_historia_usuario(h1, ejecutado_por=USER_PO_ID)
    proyecto.estimar_historia(h1.id, 5, ejecutado_por=USER_DEV_ID)
    proyecto.asociar_historia_a_sprint(h1.id, sprint.id, ejecutado_por=USER_PO_ID)
    
    # Historia 2 (8 puntos)
    h2 = HistoriaUsuario(id=uuid.uuid4(), correlativo="US-002", titulo="Historia 2", narrativa="Como...", criterios_aceptacion=["Ok"])
    proyecto.crear_historia_usuario(h2, ejecutado_por=USER_PO_ID)
    proyecto.estimar_historia(h2.id, 8, ejecutado_por=USER_DEV_ID)
    proyecto.asociar_historia_a_sprint(h2.id, sprint.id, ejecutado_por=USER_PO_ID)
    
    # Activar sprint
    proyecto.activar_sprint(sprint.id, ejecutado_por=USER_SM_ID)
    assert sprint.velocidad_comprometida == 13
    
    # Completamos la Historia 1, pero dejamos la Historia 2 incompleta (en progreso)
    # Para completar H1, debe tener todas sus tareas terminadas (si tiene) y el PO validarla.
    # En este caso, simulamos pasar H1 a HECHA (simulando aprobación del PO)
    proyecto.cambiar_estado_historia(h1.id, StoryState.HECHA, ejecutado_por=USER_PO_ID)
    
    # Cerrar el Sprint
    proyecto.cerrar_sprint(sprint.id, ejecutado_por=USER_SM_ID)
    
    assert sprint.estado == SprintState.CERRADO
    assert sprint.velocidad_realizada == 5
    
    # La historia incompleta (H2) debe desasociarse del Sprint y volver al Backlog en estado NUEVA o REFINADA
    assert h2.sprint_id is None
    assert h2.estado in [StoryState.NUEVA, StoryState.REFINADA]


# --- PRUEBAS DE TAREAS Y COHESIÓN ---

def test_creacion_de_tarea_debe_estar_vinculada_a_historia_y_modificar_estado_historia():
    proyecto = create_valid_project()
    historia = HistoriaUsuario(id=uuid.uuid4(), correlativo="US-001", titulo="Historia 1", narrativa="Como...", criterios_aceptacion=["Ok"])
    proyecto.crear_historia_usuario(historia, ejecutado_por=USER_PO_ID)
    
    # Intentar crear tarea sin historia válida debería fallar en el agregador.
    # Crear tarea para la historia
    tarea = Tarea(id=uuid.uuid4(), titulo="Tarea técnica 1", descripcion="Detalle")
    proyecto.crear_tarea_en_historia(historia.id, tarea, ejecutado_por=USER_DEV_ID)
    
    assert tarea.historia_id == historia.id
    assert tarea.estado == TaskState.PENDIENTE
    assert historia.estado == StoryState.NUEVA

    # Al cambiar el estado de la primera tarea a EN_CURSO, la historia debe pasar a EN_PROGRESO automáticamente
    proyecto.cambiar_estado_tarea(tarea.id, TaskState.EN_CURSO, ejecutado_por=USER_DEV_ID)
    assert tarea.estado == TaskState.EN_CURSO
    assert historia.estado == StoryState.EN_PROGRESO

def test_historia_no_puede_ser_hecha_si_tiene_tareas_incompletas():
    proyecto = create_valid_project()
    historia = HistoriaUsuario(id=uuid.uuid4(), correlativo="US-001", titulo="Historia 1", narrativa="Como...", criterios_aceptacion=["Ok"])
    proyecto.crear_historia_usuario(historia, ejecutado_por=USER_PO_ID)
    
    t1 = Tarea(id=uuid.uuid4(), titulo="Tarea 1", descripcion="Detalle")
    t2 = Tarea(id=uuid.uuid4(), titulo="Tarea 2", descripcion="Detalle")
    proyecto.crear_tarea_en_historia(historia.id, t1, ejecutado_por=USER_DEV_ID)
    proyecto.crear_tarea_en_historia(historia.id, t2, ejecutado_por=USER_DEV_ID)
    
    # Comenzamos la tarea 1 (Historia pasa a EN_PROGRESO)
    proyecto.cambiar_estado_tarea(t1.id, TaskState.EN_CURSO, ejecutado_por=USER_DEV_ID)
    
    # Intentamos pasar la historia a HECHA directamente sin terminar tareas, debe fallar
    with pytest.raises(BusinessRuleValidationException) as exc:
        proyecto.cambiar_estado_historia(historia.id, StoryState.HECHA, ejecutado_por=USER_PO_ID)
    assert "tiene tareas pendientes" in str(exc.value)

    # Terminamos tarea 1 y 2
    proyecto.cambiar_estado_tarea(t1.id, TaskState.TERMINADA, ejecutado_por=USER_DEV_ID)
    proyecto.cambiar_estado_tarea(t2.id, TaskState.TERMINADA, ejecutado_por=USER_DEV_ID)
    
    # Ahora sí podemos pasar a HECHA si el PO la valida
    proyecto.cambiar_estado_historia(historia.id, StoryState.HECHA, ejecutado_por=USER_PO_ID)
    assert historia.estado == StoryState.HECHA


# --- PRUEBAS DE AUTORIZACIÓN POR ROL ---

def test_autorizacion_de_roles_segun_la_matriz():
    proyecto = create_valid_project()
    # El usuario USER_DEV_ID es Developer en este proyecto
    proyecto.asignar_rol(USER_DEV_ID, ScrumRole.DEVELOPER)
    
    # 1. Product Owner crea historia de usuario -> OK
    h1 = HistoriaUsuario(id=uuid.uuid4(), correlativo="US-001", titulo="H1", narrativa="Como...", criterios_aceptacion=["Ok"])
    proyecto.crear_historia_usuario(h1, ejecutado_por=USER_PO_ID)
    
    # 2. Developer intenta crear historia de usuario -> Debe fallar
    h2 = HistoriaUsuario(id=uuid.uuid4(), correlativo="US-002", titulo="H2", narrativa="Como...", criterios_aceptacion=["Ok"])
    with pytest.raises(BusinessRuleValidationException) as exc:
        proyecto.crear_historia_usuario(h2, ejecutado_por=USER_DEV_ID)
    assert "Solo los Product Owner pueden realizar esta acción" in str(exc.value)

    # 3. Product Owner intenta estimar -> Debe fallar (solo Developer estima)
    with pytest.raises(BusinessRuleValidationException) as exc:
        proyecto.estimar_historia(h1.id, 5, ejecutado_por=USER_PO_ID)
    assert "Solo los Developers pueden realizar esta acción" in str(exc.value)
