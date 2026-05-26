import uuid
from typing import List, Optional
from src.shared_kernel.domain.exceptions import BusinessRuleValidationException
from src.shared_kernel.domain.value_objects import DateRange
from src.scrum.domain.value_objects import SprintState, StoryState, TaskState

class Sprint:
    def __init__(
        self,
        id: uuid.UUID,
        nombre: str,
        rango_fechas: DateRange,
        estado: SprintState = SprintState.PLANIFICACION,
        objetivo: str = ""
    ):
        self.id = id
        self.nombre = nombre
        self.rango_fechas = rango_fechas
        self.estado = estado
        self.objetivo = objetivo
        self.velocidad_comprometida = 0
        self.velocidad_realizada = 0

    def actualizar_rango_fechas(self, nuevo_rango: DateRange):
        if self.estado == SprintState.ACTIVO:
            raise BusinessRuleValidationException("El rango de fechas queda bloqueado y no puede ser modificado una vez el Sprint está Activo.")
        self.rango_fechas = nuevo_rango


class HistoriaUsuario:
    def __init__(
        self,
        id: uuid.UUID,
        correlativo: str,
        titulo: str,
        narrativa: str,
        criterios_aceptacion: List[str],
        esfuerzo_estimado: int = 0,
        estado: StoryState = StoryState.NUEVA,
        sprint_id: Optional[uuid.UUID] = None
    ):
        self.id = id
        self.correlativo = correlativo
        self.titulo = titulo
        self.narrativa = narrativa
        self.criterios_aceptacion = criterios_aceptacion
        self.esfuerzo_estimado = esfuerzo_estimado
        self.estado = estado
        self.sprint_id = sprint_id


class Tarea:
    def __init__(
        self,
        id: uuid.UUID,
        titulo: str,
        descripcion: str,
        estado: TaskState = TaskState.PENDIENTE,
        asignado_a: Optional[uuid.UUID] = None,
        historia_id: Optional[uuid.UUID] = None
    ):
        self.id = id
        self.titulo = titulo
        self.descripcion = descripcion
        self.estado = estado
        self.asignado_a = asignado_a
        self.historia_id = historia_id
