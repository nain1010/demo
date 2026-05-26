from enum import Enum

class ScrumRole(str, Enum):
    PRODUCT_OWNER = "Product Owner"
    SCRUM_MASTER = "Scrum Master"
    DEVELOPER = "Developer"


class SprintState(str, Enum):
    PLANIFICACION = "Planificacion"
    ACTIVO = "Activo"
    CERRADO = "Cerrado"


class StoryState(str, Enum):
    NUEVA = "Nueva"
    REFINADA = "Refinada"
    COMPROMETIDA = "Comprometida"
    EN_PROGRESO = "En Progreso"
    LISTA_PARA_PRUEBAS = "Lista para Pruebas"
    HECHA = "Hecha"


class TaskState(str, Enum):
    PENDIENTE = "Pendiente"
    EN_CURSO = "En Curso"
    BLOQUEADA = "Bloqueada"
    TERMINADA = "Terminada"
