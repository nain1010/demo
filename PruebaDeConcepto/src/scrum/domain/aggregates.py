import uuid
from datetime import date
from typing import Dict, List, Optional
from src.shared_kernel.domain.exceptions import BusinessRuleValidationException, EntityNotFoundException
from src.scrum.domain.value_objects import ScrumRole, SprintState, StoryState, TaskState
from src.scrum.domain.entities import Sprint, HistoriaUsuario, Tarea

class Proyecto:
    def __init__(
        self,
        id: uuid.UUID,
        nombre: str,
        fecha_inicio: date,
        descripcion: str = ""
    ):
        self.id = id
        self.nombre = nombre
        self.fecha_inicio = fecha_inicio
        self.descripcion = descripcion
        
        # Mapea usuario_id -> ScrumRole
        self.memberships: Dict[uuid.UUID, ScrumRole] = {}
        self.sprints: List[Sprint] = []
        self.historias_usuario: List[HistoriaUsuario] = []
        self.tareas: List[Tarea] = []

    def asignar_rol(self, usuario_id: uuid.UUID, rol: ScrumRole):
        """Asigna un rol Scrum a un usuario en el proyecto, validando exclusividad de PO y SM."""
        if rol == ScrumRole.PRODUCT_OWNER:
            for uid, r in self.memberships.items():
                if r == ScrumRole.PRODUCT_OWNER and uid != usuario_id:
                    raise BusinessRuleValidationException("Ya existe un Product Owner asignado a este proyecto.")
        elif rol == ScrumRole.SCRUM_MASTER:
            for uid, r in self.memberships.items():
                if r == ScrumRole.SCRUM_MASTER and uid != usuario_id:
                    raise BusinessRuleValidationException("Ya existe un Scrum Master asignado a este proyecto.")
        
        self.memberships[usuario_id] = rol

    def _validar_roles_minimos(self):
        """Valida que el proyecto tenga exactamente 1 PO y 1 SM antes de planificar/iniciar sprints."""
        po_exists = any(r == ScrumRole.PRODUCT_OWNER for r in self.memberships.values())
        sm_exists = any(r == ScrumRole.SCRUM_MASTER for r in self.memberships.values())
        if not po_exists or not sm_exists:
            raise BusinessRuleValidationException("Debe contar con exactamente un Product Owner y un Scrum Master asignados antes de planificar o iniciar sprints.")

    def _validar_rol(self, usuario_id: uuid.UUID, roles_permitidos: List[ScrumRole], mensaje_error: str):
        """Valida si el usuario tiene un rol permitido en el proyecto."""
        rol_usuario = self.memberships.get(usuario_id)
        if rol_usuario not in roles_permitidos:
            raise BusinessRuleValidationException(mensaje_error)

    # --- HISTORIAS DE USUARIO ---

    def crear_historia_usuario(self, historia: HistoriaUsuario, ejecutado_por: uuid.UUID):
        """Permite al Product Owner crear una historia de usuario."""
        self._validar_rol(ejecutado_por, [ScrumRole.PRODUCT_OWNER], "Solo los Product Owner pueden realizar esta acción.")
        self.historias_usuario.append(historia)

    def estimar_historia(self, historia_id: uuid.UUID, puntos: int, ejecutado_por: uuid.UUID):
        """Permite a los Developers estimar el esfuerzo de una historia de usuario usando Fibonacci."""
        self._validar_rol(ejecutado_por, [ScrumRole.DEVELOPER], "Solo los Developers pueden realizar esta acción.")
        
        if puntos not in [0, 1, 2, 3, 5, 8, 13, 21]:
            raise BusinessRuleValidationException("La estimación debe estar estrictamente en la escala Fibonacci de Scrum (0, 1, 2, 3, 5, 8, 13, 21).")
        
        historia = next((h for h in self.historias_usuario if h.id == historia_id), None)
        if not historia:
            raise EntityNotFoundException(f"Historia de usuario con id {historia_id} no encontrada.")
        
        historia.esfuerzo_estimado = puntos

    def asociar_historia_a_sprint(self, historia_id: uuid.UUID, sprint_id: uuid.UUID, ejecutado_por: uuid.UUID):
        """Asocia una historia a un sprint en fase de planificación."""
        self._validar_rol(ejecutado_por, [ScrumRole.PRODUCT_OWNER, ScrumRole.SCRUM_MASTER], "Solo el Product Owner o el Scrum Master pueden planificar sprints.")
        self._validar_roles_minimos()
        
        historia = next((h for h in self.historias_usuario if h.id == historia_id), None)
        if not historia:
            raise EntityNotFoundException(f"Historia de usuario con id {historia_id} no encontrada.")
            
        sprint = next((s for s in self.sprints if s.id == sprint_id), None)
        if not sprint:
            raise EntityNotFoundException(f"Sprint con id {sprint_id} no encontrado.")
            
        historia.sprint_id = sprint_id
        historia.estado = StoryState.COMPROMETIDA

    def cambiar_estado_historia(self, historia_id: uuid.UUID, nuevo_estado: StoryState, ejecutado_por: uuid.UUID):
        """Cambia el estado de una historia de usuario, validando criterios de aceptación y roles."""
        historia = next((h for h in self.historias_usuario if h.id == historia_id), None)
        if not historia:
            raise EntityNotFoundException(f"Historia de usuario con id {historia_id} no encontrada.")

        if nuevo_estado == StoryState.HECHA:
            self._validar_rol(ejecutado_por, [ScrumRole.PRODUCT_OWNER], "Solo el Product Owner puede validar criterios de aceptación y marcar la historia como hecha.")
            
            # Validar que todas las tareas estén completadas
            tareas_hijas = [t for t in self.tareas if t.historia_id == historia_id]
            if any(t.estado != TaskState.TERMINADA for t in tareas_hijas):
                raise BusinessRuleValidationException("La historia tiene tareas pendientes y no puede ser marcada como hecha.")
        
        historia.estado = nuevo_estado

    # --- SPRINTS ---

    def agregar_sprint(self, sprint: Sprint):
        """Agrega un sprint al proyecto (fase planificación), validando roles mínimos."""
        self._validar_roles_minimos()
        self.sprints.append(sprint)

    def activar_sprint(self, sprint_id: uuid.UUID, ejecutado_por: uuid.UUID):
        """Activa un sprint, garantizando exclusividad y estimación de sus historias."""
        self._validar_rol(ejecutado_por, [ScrumRole.SCRUM_MASTER], "Solo los Scrum Master pueden realizar esta acción.")
        self._validar_roles_minimos()
        
        sprint_a_activar = next((s for s in self.sprints if s.id == sprint_id), None)
        if not sprint_a_activar:
            raise EntityNotFoundException(f"Sprint con id {sprint_id} no encontrado.")
            
        # Validar que no haya otro sprint activo
        if any(s.estado == SprintState.ACTIVO for s in self.sprints):
            raise BusinessRuleValidationException("Un Sprint no puede pasar a estado 'Activo' si existe otro Sprint actualmente activo en el mismo Proyecto.")
            
        # Validar estimación de historias
        historias_sprint = [h for h in self.historias_usuario if h.sprint_id == sprint_id]
        if any(h.esfuerzo_estimado == 0 for h in historias_sprint):
            raise BusinessRuleValidationException("Una historia sin estimar (0 puntos) no puede ingresar a un Sprint activo.")
            
        sprint_a_activar.estado = SprintState.ACTIVO
        sprint_a_activar.velocidad_comprometida = sum(h.esfuerzo_estimado for h in historias_sprint)

    def cerrar_sprint(self, sprint_id: uuid.UUID, ejecutado_por: uuid.UUID):
        """Cierra un sprint, calculando velocidad real y desasociando historias pendientes."""
        self._validar_rol(ejecutado_por, [ScrumRole.SCRUM_MASTER], "Solo los Scrum Master pueden realizar esta acción.")
        
        sprint = next((s for s in self.sprints if s.id == sprint_id), None)
        if not sprint:
            raise EntityNotFoundException(f"Sprint con id {sprint_id} no encontrado.")
            
        sprint.estado = SprintState.CERRADO
        
        historias_sprint = [h for h in self.historias_usuario if h.sprint_id == sprint_id]
        
        # Las historias HECHAS computan para velocidad_realizada
        historias_hechas = [h for h in historias_sprint if h.estado == StoryState.HECHA]
        sprint.velocidad_realizada = sum(h.esfuerzo_estimado for h in historias_hechas)
        
        # Las incompletas vuelven al backlog (sprint_id = None) y estado Nueva o Refinada
        historias_incompletas = [h for h in historias_sprint if h.estado != StoryState.HECHA]
        for h in historias_incompletas:
            h.sprint_id = None
            h.estado = StoryState.REFINADA if h.esfuerzo_estimado > 0 else StoryState.NUEVA

    # --- TAREAS ---

    def crear_tarea_en_historia(self, historia_id: uuid.UUID, tarea: Tarea, ejecutado_por: uuid.UUID):
        """Crea una tarea técnica asignada a una historia de usuario."""
        self._validar_rol(ejecutado_por, [ScrumRole.DEVELOPER], "Solo los Developers pueden realizar esta acción.")
        
        historia = next((h for h in self.historias_usuario if h.id == historia_id), None)
        if not historia:
            raise EntityNotFoundException(f"Historia de usuario con id {historia_id} no encontrada.")
            
        tarea.historia_id = historia_id
        tarea.estado = TaskState.PENDIENTE
        self.tareas.append(tarea)

    def cambiar_estado_tarea(self, tarea_id: uuid.UUID, nuevo_estado: TaskState, ejecutado_por: uuid.UUID):
        """Cambia el estado de una tarea técnica y actualiza el estado de la historia de usuario."""
        self._validar_rol(ejecutado_por, [ScrumRole.DEVELOPER], "Solo los Developers pueden realizar esta acción.")
        
        tarea = next((t for t in self.tareas if t.id == tarea_id), None)
        if not tarea:
            raise EntityNotFoundException(f"Tarea con id {tarea_id} no encontrada.")
            
        tarea.estado = nuevo_estado
        
        # Sincronización automática del estado de la historia
        if nuevo_estado == TaskState.EN_CURSO:
            historia = next((h for h in self.historias_usuario if h.id == tarea.historia_id), None)
            if historia and historia.estado == StoryState.COMPROMETIDA or (historia and historia.estado == StoryState.NUEVA):
                historia.estado = StoryState.EN_PROGRESO
