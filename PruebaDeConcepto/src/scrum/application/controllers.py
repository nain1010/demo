import uuid
from datetime import date
from typing import List, Optional
from litestar import Controller, post, put, Request
from pydantic import BaseModel
from src.scrum.domain.ports import ScrumRepositoryPort
from src.scrum.domain.aggregates import Proyecto
from src.scrum.domain.entities import Sprint, HistoriaUsuario, Tarea
from src.scrum.domain.value_objects import ScrumRole, SprintState, StoryState, TaskState
from src.shared_kernel.domain.value_objects import DateRange
from src.shared_kernel.domain.exceptions import EntityNotFoundException, BusinessRuleValidationException
from src.shared_kernel.infrastructure.guards import guard_authenticated, guard_admin, check_project_role

# --- DTOs ---

class CreateProjectDTO(BaseModel):
    nombre: str
    descripcion: str = ""
    fecha_inicio: date


class AssignMemberDTO(BaseModel):
    usuario_id: uuid.UUID
    rol: ScrumRole


class CreateSprintDTO(BaseModel):
    nombre: str
    fecha_inicio: date
    fecha_fin: date
    objetivo: str = ""


class CreateStoryDTO(BaseModel):
    correlativo: str
    titulo: str
    narrativa: str
    criterios_aceptacion: List[str]


class EstimateStoryDTO(BaseModel):
    puntos: int


class PlanStoryDTO(BaseModel):
    sprint_id: uuid.UUID


class ChangeStoryStatusDTO(BaseModel):
    estado: StoryState


class CreateTaskDTO(BaseModel):
    titulo: str
    descripcion: str


class ChangeTaskStatusDTO(BaseModel):
    estado: TaskState


# --- CONTROLLERS ---

class ProjectController(Controller):
    path = "/projects"
    guards = [guard_authenticated]

    @post("", guards=[guard_admin])
    async def create_project(self, data: CreateProjectDTO, scrum_repository: ScrumRepositoryPort) -> dict:
        """Crea un nuevo proyecto en el sistema (requiere rol global Administrador)."""
        proyecto_id = uuid.uuid4()
        proyecto = Proyecto(
            id=proyecto_id,
            nombre=data.nombre,
            descripcion=data.descripcion,
            fecha_inicio=data.fecha_inicio
        )
        await scrum_repository.save(proyecto)
        return {"id": str(proyecto_id), "nombre": proyecto.nombre}

    @post("/{project_id:uuid}/members", guards=[guard_admin])
    async def assign_member(
        self,
        project_id: uuid.UUID,
        data: AssignMemberDTO,
        scrum_repository: ScrumRepositoryPort
    ) -> dict:
        """Asigna un rol Scrum a un usuario en el proyecto (requiere Administrador)."""
        proyecto = await scrum_repository.get_by_id(project_id)
        if not proyecto:
            raise EntityNotFoundException(f"Proyecto con id {project_id} no encontrado.")
        
        proyecto.asignar_rol(data.usuario_id, data.rol)
        await scrum_repository.save(proyecto)
        return {"message": f"Usuario {data.usuario_id} asignado como {data.rol.value}."}

    @post("/{project_id:uuid}/sprints", guards=[check_project_role([ScrumRole.PRODUCT_OWNER, ScrumRole.SCRUM_MASTER])])
    async def create_sprint(
        self,
        project_id: uuid.UUID,
        data: CreateSprintDTO,
        scrum_repository: ScrumRepositoryPort
    ) -> dict:
        """Agrega un Sprint en fase de planificación (requiere PO o SM del proyecto)."""
        proyecto = await scrum_repository.get_by_id(project_id)
        if not proyecto:
            raise EntityNotFoundException(f"Proyecto con id {project_id} no encontrado.")
        
        sprint_id = uuid.uuid4()
        sprint = Sprint(
            id=sprint_id,
            nombre=data.nombre,
            rango_fechas=DateRange(data.fecha_inicio, data.fecha_fin),
            objetivo=data.objetivo
        )
        proyecto.agregar_sprint(sprint)
        await scrum_repository.save(proyecto)
        return {"id": str(sprint_id), "nombre": sprint.nombre, "estado": sprint.estado.value}

    @post("/{project_id:uuid}/sprints/{sprint_id:uuid}/activate", guards=[check_project_role([ScrumRole.SCRUM_MASTER])])
    async def activate_sprint(
        self,
        project_id: uuid.UUID,
        sprint_id: uuid.UUID,
        request: Request,
        scrum_repository: ScrumRepositoryPort
    ) -> dict:
        """Activa un Sprint, iniciando el flujo de trabajo (requiere SM del proyecto)."""
        proyecto = await scrum_repository.get_by_id(project_id)
        if not proyecto:
            raise EntityNotFoundException(f"Proyecto con id {project_id} no encontrado.")
        
        proyecto.activar_sprint(sprint_id, ejecutado_por=request.state.user.id)
        await scrum_repository.save(proyecto)
        
        # Encontrar sprint activado para devolver detalles
        sprint = next(s for s in proyecto.sprints if s.id == sprint_id)
        return {
            "id": str(sprint_id),
            "estado": sprint.estado.value,
            "velocidad_comprometida": sprint.velocidad_comprometida
        }

    @post("/{project_id:uuid}/sprints/{sprint_id:uuid}/close", guards=[check_project_role([ScrumRole.SCRUM_MASTER])])
    async def close_sprint(
        self,
        project_id: uuid.UUID,
        sprint_id: uuid.UUID,
        request: Request,
        scrum_repository: ScrumRepositoryPort
    ) -> dict:
        """Cierra un Sprint activo, calcula velocidades y devuelve historias sin terminar al backlog (requiere SM)."""
        proyecto = await scrum_repository.get_by_id(project_id)
        if not proyecto:
            raise EntityNotFoundException(f"Proyecto con id {project_id} no encontrado.")
        
        proyecto.cerrar_sprint(sprint_id, ejecutado_por=request.state.user.id)
        await scrum_repository.save(proyecto)
        
        sprint = next(s for s in proyecto.sprints if s.id == sprint_id)
        return {
            "id": str(sprint_id),
            "estado": sprint.estado.value,
            "velocidad_realizada": sprint.velocidad_realizada
        }

    @post("/{project_id:uuid}/stories", guards=[check_project_role([ScrumRole.PRODUCT_OWNER])])
    async def create_story(
        self,
        project_id: uuid.UUID,
        data: CreateStoryDTO,
        request: Request,
        scrum_repository: ScrumRepositoryPort
    ) -> dict:
        """Crea una Historia de Usuario en el Product Backlog (requiere PO)."""
        proyecto = await scrum_repository.get_by_id(project_id)
        if not proyecto:
            raise EntityNotFoundException(f"Proyecto con id {project_id} no encontrado.")
        
        story_id = uuid.uuid4()
        story = HistoriaUsuario(
            id=story_id,
            correlativo=data.correlativo,
            titulo=data.titulo,
            narrativa=data.narrativa,
            criterios_aceptacion=data.criterios_aceptacion
        )
        proyecto.crear_historia_usuario(story, ejecutado_por=request.state.user.id)
        await scrum_repository.save(proyecto)
        return {"id": str(story_id), "correlativo": story.correlativo, "estado": story.estado.value}

    @post("/{project_id:uuid}/stories/{story_id:uuid}/estimate", guards=[check_project_role([ScrumRole.DEVELOPER])])
    async def estimate_story(
        self,
        project_id: uuid.UUID,
        story_id: uuid.UUID,
        data: EstimateStoryDTO,
        request: Request,
        scrum_repository: ScrumRepositoryPort
    ) -> dict:
        """Estima los puntos de esfuerzo de una historia de usuario usando Fibonacci (requiere Developer)."""
        proyecto = await scrum_repository.get_by_id(project_id)
        if not proyecto:
            raise EntityNotFoundException(f"Proyecto con id {project_id} no encontrado.")
        
        proyecto.estimar_historia(story_id, data.puntos, ejecutado_por=request.state.user.id)
        await scrum_repository.save(proyecto)
        return {"message": "Historia estimada correctamente.", "puntos": data.puntos}

    @post("/{project_id:uuid}/stories/{story_id:uuid}/sprint", guards=[check_project_role([ScrumRole.PRODUCT_OWNER, ScrumRole.SCRUM_MASTER])])
    async def plan_story(
        self,
        project_id: uuid.UUID,
        story_id: uuid.UUID,
        data: PlanStoryDTO,
        request: Request,
        scrum_repository: ScrumRepositoryPort
    ) -> dict:
        """Asocia una Historia de Usuario a un Sprint en fase de planificación (requiere PO o SM)."""
        proyecto = await scrum_repository.get_by_id(project_id)
        if not proyecto:
            raise EntityNotFoundException(f"Proyecto con id {project_id} no encontrado.")
        
        proyecto.asociar_historia_a_sprint(story_id, data.sprint_id, ejecutado_por=request.state.user.id)
        await scrum_repository.save(proyecto)
        return {"message": "Historia asociada al Sprint correctamente.", "sprint_id": str(data.sprint_id)}

    @put("/{project_id:uuid}/stories/{story_id:uuid}/status", guards=[guard_authenticated])
    async def change_story_status(
        self,
        project_id: uuid.UUID,
        story_id: uuid.UUID,
        data: ChangeStoryStatusDTO,
        request: Request,
        scrum_repository: ScrumRepositoryPort
    ) -> dict:
        """Cambia el estado de una Historia de Usuario (Marcar como HECHA requiere PO)."""
        proyecto = await scrum_repository.get_by_id(project_id)
        if not proyecto:
            raise EntityNotFoundException(f"Proyecto con id {project_id} no encontrado.")
        
        # Validar permisos a nivel de controlador para rol global y Scrum según el estado
        # Si se quiere pasar a HECHA, se valida que sea el PO del proyecto
        proyecto.cambiar_estado_historia(story_id, data.estado, ejecutado_por=request.state.user.id)
        await scrum_repository.save(proyecto)
        return {"id": str(story_id), "nuevo_estado": data.estado.value}

    @post("/{project_id:uuid}/stories/{story_id:uuid}/tasks", guards=[check_project_role([ScrumRole.DEVELOPER])])
    async def create_task(
        self,
        project_id: uuid.UUID,
        story_id: uuid.UUID,
        data: CreateTaskDTO,
        request: Request,
        scrum_repository: ScrumRepositoryPort
    ) -> dict:
        """Crea una tarea técnica vinculada a una Historia de Usuario (requiere Developer)."""
        proyecto = await scrum_repository.get_by_id(project_id)
        if not proyecto:
            raise EntityNotFoundException(f"Proyecto con id {project_id} no encontrado.")
        
        task_id = uuid.uuid4()
        tarea = Tarea(
            id=task_id,
            titulo=data.titulo,
            descripcion=data.descripcion
        )
        proyecto.crear_tarea_en_historia(story_id, tarea, ejecutado_por=request.state.user.id)
        await scrum_repository.save(proyecto)
        return {"id": str(task_id), "titulo": tarea.titulo, "estado": tarea.estado.value}

    @put("/{project_id:uuid}/tasks/{task_id:uuid}/status", guards=[check_project_role([ScrumRole.DEVELOPER])])
    async def change_task_status(
        self,
        project_id: uuid.UUID,
        task_id: uuid.UUID,
        data: ChangeTaskStatusDTO,
        request: Request,
        scrum_repository: ScrumRepositoryPort
    ) -> dict:
        """Cambia el estado de una Tarea Técnica (requiere Developer)."""
        proyecto = await scrum_repository.get_by_id(project_id)
        if not proyecto:
            raise EntityNotFoundException(f"Proyecto con id {project_id} no encontrado.")
        
        proyecto.cambiar_estado_tarea(task_id, data.estado, ejecutado_por=request.state.user.id)
        await scrum_repository.save(proyecto)
        return {"id": str(task_id), "nuevo_estado": data.estado.value}
