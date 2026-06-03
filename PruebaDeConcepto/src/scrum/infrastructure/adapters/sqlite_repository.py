import uuid
from typing import Optional
# pyrefly: ignore [missing-import]
from sqlalchemy import select, delete
# pyrefly: ignore [missing-import]
from sqlalchemy.ext.asyncio import AsyncSession
from src.scrum.domain.ports import ScrumRepositoryPort
from src.scrum.domain.aggregates import Proyecto
from src.scrum.domain.entities import Sprint, HistoriaUsuario, Tarea
from src.scrum.domain.value_objects import ScrumRole, SprintState, StoryState, TaskState
from src.shared_kernel.domain.value_objects import DateRange
from src.scrum.infrastructure.models import (
    ProyectoModel,
    ProyectoMembershipModel,
    SprintModel,
    HistoriaUsuarioModel,
    TareaModel
)

class SqliteScrumRepository(ScrumRepositoryPort):
    """Implementación del puerto de persistencia Scrum en SQLite/Turso usando SQLAlchemy asíncrono."""
    
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, proyecto: Proyecto) -> None:
        """Guarda de forma atómica el estado actual del agregado Proyecto."""
        # 1. Upsert Proyecto
        proj_model = ProyectoModel(
            id=str(proyecto.id),
            nombre=proyecto.nombre,
            descripcion=proyecto.descripcion,
            fecha_inicio=proyecto.fecha_inicio
        )
        await self.session.merge(proj_model)

        # 2. Sincronizar Memberships (borrar y re-insertar)
        await self.session.execute(
            delete(ProyectoMembershipModel).where(ProyectoMembershipModel.proyecto_id == str(proyecto.id))
        )
        for user_id, rol in proyecto.memberships.items():
            membership = ProyectoMembershipModel(
                proyecto_id=str(proyecto.id),
                usuario_id=str(user_id),
                rol=rol.value
            )
            self.session.add(membership)

        # 3. Sincronizar Sprints
        sprint_ids = [str(s.id) for s in proyecto.sprints]
        await self.session.execute(
            delete(SprintModel).where(
                (SprintModel.proyecto_id == str(proyecto.id)) & (~SprintModel.id.in_(sprint_ids))
            )
        )
        for sprint in proyecto.sprints:
            sprint_model = SprintModel(
                id=str(sprint.id),
                proyecto_id=str(proyecto.id),
                nombre=sprint.nombre,
                fecha_inicio=sprint.rango_fechas.start_date,
                fecha_fin=sprint.rango_fechas.end_date,
                estado=sprint.estado.value,
                velocidad_comprometida=sprint.velocidad_comprometida,
                velocidad_realizada=sprint.velocidad_realizada,
                objetivo=sprint.objetivo
            )
            await self.session.merge(sprint_model)

        # 4. Sincronizar Historias de Usuario
        story_ids = [str(h.id) for h in proyecto.historias_usuario]
        await self.session.execute(
            delete(HistoriaUsuarioModel).where(
                (HistoriaUsuarioModel.proyecto_id == str(proyecto.id)) & (~HistoriaUsuarioModel.id.in_(story_ids))
            )
        )
        for story in proyecto.historias_usuario:
            story_model = HistoriaUsuarioModel(
                id=str(story.id),
                proyecto_id=str(proyecto.id),
                sprint_id=str(story.sprint_id) if story.sprint_id else None,
                correlativo=story.correlativo,
                titulo=story.titulo,
                narrativa=story.narrativa,
                criterios_aceptacion=story.criterios_aceptacion,
                esfuerzo_estimado=story.esfuerzo_estimado,
                estado=story.estado.value
            )
            await self.session.merge(story_model)

        # 5. Sincronizar Tareas
        task_ids = [str(t.id) for t in proyecto.tareas]
        story_ids_str = [str(h.id) for h in proyecto.historias_usuario]
        if story_ids_str:
            await self.session.execute(
                delete(TareaModel).where(
                    (TareaModel.historia_id.in_(story_ids_str)) & (~TareaModel.id.in_(task_ids))
                )
            )
        for task in proyecto.tareas:
            task_model = TareaModel(
                id=str(task.id),
                historia_id=str(task.historia_id),
                titulo=task.titulo,
                descripcion=task.descripcion,
                estado=task.estado.value,
                asignado_a=str(task.asignado_a) if task.asignado_a else None
            )
            await self.session.merge(task_model)

        await self.session.flush()
        await self.session.commit()

    async def get_by_id(self, proyecto_id: uuid.UUID) -> Optional[Proyecto]:
        """Carga y reconstruye el agregado Proyecto completo desde la persistencia."""
        # 1. Cargar el Proyecto
        res = await self.session.execute(
            select(ProyectoModel).where(ProyectoModel.id == str(proyecto_id))
        )
        proj_model = res.scalar_one_or_none()
        if not proj_model:
            return None

        proyecto = Proyecto(
            id=uuid.UUID(proj_model.id),
            nombre=proj_model.nombre,
            descripcion=proj_model.descripcion,
            fecha_inicio=proj_model.fecha_inicio
        )

        # 2. Cargar Memberships
        res_mem = await self.session.execute(
            select(ProyectoMembershipModel).where(ProyectoMembershipModel.proyecto_id == str(proyecto_id))
        )
        for mem in res_mem.scalars():
            proyecto.memberships[uuid.UUID(mem.usuario_id)] = ScrumRole(mem.rol)

        # 3. Cargar Sprints
        res_spr = await self.session.execute(
            select(SprintModel).where(SprintModel.proyecto_id == str(proyecto_id))
        )
        for spr in res_spr.scalars():
            sprint = Sprint(
                id=uuid.UUID(spr.id),
                nombre=spr.nombre,
                rango_fechas=DateRange(spr.fecha_inicio, spr.fecha_fin),
                estado=SprintState(spr.estado),
                objetivo=spr.objetivo
            )
            sprint.velocidad_comprometida = spr.velocidad_comprometida
            sprint.velocidad_realizada = spr.velocidad_realizada
            proyecto.sprints.append(sprint)

        # 4. Cargar Historias de Usuario
        res_story = await self.session.execute(
            select(HistoriaUsuarioModel).where(HistoriaUsuarioModel.proyecto_id == str(proyecto_id))
        )
        story_ids = []
        for st in res_story.scalars():
            story = HistoriaUsuario(
                id=uuid.UUID(st.id),
                correlativo=st.correlativo,
                titulo=st.titulo,
                narrativa=st.narrativa,
                criterios_aceptacion=st.criterios_aceptacion,
                esfuerzo_estimado=st.esfuerzo_estimado,
                estado=StoryState(st.estado),
                sprint_id=uuid.UUID(st.sprint_id) if st.sprint_id else None
            )
            proyecto.historias_usuario.append(story)
            story_ids.append(st.id)

        # 5. Cargar Tareas
        if story_ids:
            res_task = await self.session.execute(
                select(TareaModel).where(TareaModel.historia_id.in_(story_ids))
            )
            for tk in res_task.scalars():
                tarea = Tarea(
                    id=uuid.UUID(tk.id),
                    titulo=tk.titulo,
                    descripcion=tk.descripcion,
                    estado=TaskState(tk.estado),
                    asignado_a=uuid.UUID(tk.asignado_a) if tk.asignado_a else None,
                    historia_id=uuid.UUID(tk.historia_id)
                )
                proyecto.tareas.append(tarea)

        return proyecto
