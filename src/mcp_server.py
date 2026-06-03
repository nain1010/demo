import os
import sys
import uuid
from datetime import date
from pathlib import Path
from typing import List, Literal

# Asegurar que el directorio raíz del proyecto esté en el path de Python
root_path = Path(__file__).parent.parent.resolve()
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

from fastmcp import FastMCP
from sqlalchemy import text

# Importar las sesiones de base de datos del proyecto
from src.scrum.infrastructure.database import SessionLocal as ScrumSessionLocal
from src.idp.infrastructure.database import SessionLocal as IdpSessionLocal

# Importar agregados, entidades, value objects y adaptadores
from src.scrum.domain.aggregates import Proyecto
from src.scrum.domain.entities import Sprint, HistoriaUsuario, Tarea
from src.scrum.domain.value_objects import ScrumRole, SprintState, StoryState, TaskState
from src.shared_kernel.domain.value_objects import DateRange
from src.scrum.infrastructure.adapters.sqlite_repository import SqliteScrumRepository
from src.shared_kernel.domain.exceptions import DomainException

# Inicializar el servidor MCP
mcp = FastMCP("Scrum Monolith Assistant")

# --- HERRAMIENTAS DE LECTURA (READ TOOLS) ---

@mcp.tool
async def query_db(sql_query: str, db_name: Literal["scrum", "idp"] = "scrum") -> str:
    """
    Ejecuta una consulta SQL SELECT de solo lectura sobre las bases de datos locales (scrum o idp).
    Permite auditar el estado de los proyectos, membresías, historias, tareas, usuarios o la tabla outbox.
    """
    clean_query = sql_query.strip()
    if not clean_query.lower().startswith("select"):
        return "Error: Solo se permiten consultas de lectura (SELECT)."

    session_factory = ScrumSessionLocal if db_name == "scrum" else IdpSessionLocal
    
    try:
        async with session_factory() as session:
            result = await session.execute(text(clean_query))
            rows = result.fetchall()
            keys = result.keys()
            
            if not rows:
                return f"Consulta ejecutada con éxito en '{db_name}'. Sin resultados."
            
            # Formatear salida como una tabla markdown para mejor legibilidad
            header = " | ".join(keys)
            separator = " | ".join(["---"] * len(keys))
            markdown_rows = [f"| {header} |", f"| {separator} |"]
            
            for row in rows:
                formatted_values = [str(val) for val in row]
                markdown_rows.append(f"| {' | '.join(formatted_values)} |")
                
            return "\n".join(markdown_rows)
    except Exception as e:
        return f"Error ejecutando consulta en base de datos '{db_name}': {str(e)}"


@mcp.tool
async def get_projects() -> str:
    """
    Obtiene la lista de todos los proyectos creados en el sistema con sus identificadores.
    """
    query = "SELECT id, nombre, descripcion, fecha_inicio FROM proyectos"
    return await query_db(query, db_name="scrum")


# --- HERRAMIENTAS DE ESCRITURA (WRITE TOOLS) ---

@mcp.tool
async def create_project(nombre: str, fecha_inicio_iso: str, descripcion: str = "") -> str:
    """
    Crea un nuevo proyecto en el sistema.
    fecha_inicio_iso debe tener formato ISO YYYY-MM-DD.
    """
    try:
        start_date = date.fromisoformat(fecha_inicio_iso)
    except ValueError:
        return "Error: La fecha de inicio debe tener formato YYYY-MM-DD."
        
    proyecto_id = uuid.uuid4()
    proyecto = Proyecto(
        id=proyecto_id,
        nombre=nombre,
        descripcion=descripcion,
        fecha_inicio=start_date
    )
    
    async with ScrumSessionLocal() as session:
        repo = SqliteScrumRepository(session)
        try:
            await repo.save(proyecto)
            return f"Éxito: Proyecto '{nombre}' creado con ID: {proyecto_id}"
        except Exception as e:
            return f"Error guardando el proyecto: {str(e)}"


@mcp.tool
async def assign_project_member(
    proyecto_id: str,
    usuario_id: str,
    rol: Literal["Product Owner", "Scrum Master", "Developer"]
) -> str:
    """
    Asigna un rol Scrum a un usuario en un proyecto.
    Valida la exclusividad de Product Owner (PO) y Scrum Master (SM).
    """
    try:
        proj_uuid = uuid.UUID(proyecto_id)
        user_uuid = uuid.UUID(usuario_id)
        scrum_role = ScrumRole(rol)
    except ValueError:
        return "Error: IDs inválidos (deben ser UUIDs) o rol no soportado."

    async with ScrumSessionLocal() as session:
        repo = SqliteScrumRepository(session)
        proyecto = await repo.get_by_id(proj_uuid)
        if not proyecto:
            return f"Error: Proyecto con ID {proyecto_id} no encontrado."
            
        try:
            proyecto.asignar_rol(user_uuid, scrum_role)
            await repo.save(proyecto)
            return f"Éxito: Usuario {usuario_id} asignado como '{rol}' en el proyecto '{proyecto.nombre}'."
        except DomainException as e:
            return f"Error de dominio: {e.message}"
        except Exception as e:
            return f"Error inesperado: {str(e)}"


@mcp.tool
async def create_sprint(
    proyecto_id: str,
    nombre: str,
    fecha_inicio_iso: str,
    fecha_fin_iso: str,
    objetivo: str = ""
) -> str:
    """
    Agrega un Sprint en fase de planificación a un proyecto.
    Las fechas deben tener formato YYYY-MM-DD.
    """
    try:
        proj_uuid = uuid.UUID(proyecto_id)
        start_date = date.fromisoformat(fecha_inicio_iso)
        end_date = date.fromisoformat(fecha_fin_iso)
    except ValueError:
        return "Error: Formato de IDs (UUID) o fechas (YYYY-MM-DD) inválido."

    sprint_id = uuid.uuid4()
    sprint = Sprint(
        id=sprint_id,
        nombre=nombre,
        rango_fechas=DateRange(start_date, end_date),
        objetivo=objetivo
    )

    async with ScrumSessionLocal() as session:
        repo = SqliteScrumRepository(session)
        proyecto = await repo.get_by_id(proj_uuid)
        if not proyecto:
            return f"Error: Proyecto con ID {proyecto_id} no encontrado."

        try:
            proyecto.agregar_sprint(sprint)
            await repo.save(proyecto)
            return f"Éxito: Sprint '{nombre}' creado con ID: {sprint_id} para el proyecto '{proyecto.nombre}'."
        except DomainException as e:
            return f"Error de dominio: {e.message}"
        except Exception as e:
            return f"Error inesperado: {str(e)}"


@mcp.tool
async def create_user_story(
    proyecto_id: str,
    correlativo: str,
    titulo: str,
    narrativa: str,
    criterios_aceptacion: List[str],
    ejecutado_por_usuario_id: str
) -> str:
    """
    Crea una Historia de Usuario en el Product Backlog.
    Requiere que quien lo ejecuta sea el Product Owner del proyecto.
    """
    try:
        proj_uuid = uuid.UUID(proyecto_id)
        user_uuid = uuid.UUID(ejecutado_por_usuario_id)
    except ValueError:
        return "Error: IDs de proyecto o usuario inválidos (deben ser UUIDs)."

    story_id = uuid.uuid4()
    story = HistoriaUsuario(
        id=story_id,
        correlativo=correlativo,
        titulo=titulo,
        narrativa=narrativa,
        criterios_aceptacion=criterios_aceptacion
    )

    async with ScrumSessionLocal() as session:
        repo = SqliteScrumRepository(session)
        proyecto = await repo.get_by_id(proj_uuid)
        if not proyecto:
            return f"Error: Proyecto con ID {proyecto_id} no encontrado."

        try:
            proyecto.crear_historia_usuario(story, ejecutado_por=user_uuid)
            await repo.save(proyecto)
            return f"Éxito: Historia '{correlativo}' creada con ID: {story_id} en el proyecto '{proyecto.nombre}'."
        except DomainException as e:
            return f"Error de dominio: {e.message}"
        except Exception as e:
            return f"Error inesperado: {str(e)}"


@mcp.tool
async def estimate_user_story(
    proyecto_id: str,
    story_id: str,
    puntos: int,
    ejecutado_por_usuario_id: str
) -> str:
    """
    Estima los puntos de esfuerzo de una historia de usuario usando la escala Fibonacci (0, 1, 2, 3, 5, 8, 13, 21).
    Requiere que quien lo ejecuta sea Developer en el proyecto.
    """
    try:
        proj_uuid = uuid.UUID(proyecto_id)
        story_uuid = uuid.UUID(story_id)
        user_uuid = uuid.UUID(ejecutado_por_usuario_id)
    except ValueError:
        return "Error: IDs inválidos (deben ser UUIDs)."

    async with ScrumSessionLocal() as session:
        repo = SqliteScrumRepository(session)
        proyecto = await repo.get_by_id(proj_uuid)
        if not proyecto:
            return f"Error: Proyecto con ID {proyecto_id} no encontrado."

        try:
            proyecto.estimar_historia(story_uuid, puntos, ejecutado_por=user_uuid)
            await repo.save(proyecto)
            return f"Éxito: Historia {story_id} estimada en {puntos} puntos."
        except DomainException as e:
            return f"Error de dominio: {e.message}"
        except Exception as e:
            return f"Error inesperado: {str(e)}"


@mcp.tool
async def plan_story_to_sprint(
    proyecto_id: str,
    story_id: str,
    sprint_id: str,
    ejecutado_por_usuario_id: str
) -> str:
    """
    Asocia una historia a un sprint en fase de planificación.
    Requiere ser Product Owner o Scrum Master del proyecto.
    """
    try:
        proj_uuid = uuid.UUID(proyecto_id)
        story_uuid = uuid.UUID(story_id)
        sprint_uuid = uuid.UUID(sprint_id)
        user_uuid = uuid.UUID(ejecutado_por_usuario_id)
    except ValueError:
        return "Error: IDs inválidos (deben ser UUIDs)."

    async with ScrumSessionLocal() as session:
        repo = SqliteScrumRepository(session)
        proyecto = await repo.get_by_id(proj_uuid)
        if not proyecto:
            return f"Error: Proyecto con ID {proyecto_id} no encontrado."

        try:
            proyecto.asociar_historia_a_sprint(story_uuid, sprint_uuid, ejecutado_por=user_uuid)
            await repo.save(proyecto)
            return f"Éxito: Historia {story_id} asociada al sprint {sprint_id}."
        except DomainException as e:
            return f"Error de dominio: {e.message}"
        except Exception as e:
            return f"Error inesperado: {str(e)}"


@mcp.tool
async def activate_sprint(
    proyecto_id: str,
    sprint_id: str,
    ejecutado_por_usuario_id: str
) -> str:
    """
    Activa un sprint iniciando el ciclo de desarrollo.
    Requiere ser el Scrum Master del proyecto. Valida que no haya otro sprint activo
    y que todas las historias asociadas al sprint estén previamente estimadas.
    """
    try:
        proj_uuid = uuid.UUID(proyecto_id)
        sprint_uuid = uuid.UUID(sprint_id)
        user_uuid = uuid.UUID(ejecutado_por_usuario_id)
    except ValueError:
        return "Error: IDs inválidos (deben ser UUIDs)."

    async with ScrumSessionLocal() as session:
        repo = SqliteScrumRepository(session)
        proyecto = await repo.get_by_id(proj_uuid)
        if not proyecto:
            return f"Error: Proyecto con ID {proyecto_id} no encontrado."

        try:
            proyecto.activar_sprint(sprint_uuid, ejecutado_por=user_uuid)
            await repo.save(proyecto)
            return f"Éxito: Sprint {sprint_id} activado correctamente."
        except DomainException as e:
            return f"Error de dominio: {e.message}"
        except Exception as e:
            return f"Error inesperado: {str(e)}"


@mcp.tool
async def create_task_in_story(
    proyecto_id: str,
    story_id: str,
    titulo: str,
    descripcion: str,
    ejecutado_por_usuario_id: str
) -> str:
    """
    Crea una tarea técnica vinculada a una historia de usuario.
    Requiere ser Developer del proyecto.
    """
    try:
        proj_uuid = uuid.UUID(proyecto_id)
        story_uuid = uuid.UUID(story_id)
        user_uuid = uuid.UUID(ejecutado_por_usuario_id)
    except ValueError:
        return "Error: IDs inválidos (deben ser UUIDs)."

    task_id = uuid.uuid4()
    tarea = Tarea(
        id=task_id,
        titulo=titulo,
        descripcion=descripcion
    )

    async with ScrumSessionLocal() as session:
        repo = SqliteScrumRepository(session)
        proyecto = await repo.get_by_id(proj_uuid)
        if not proyecto:
            return f"Error: Proyecto con ID {proyecto_id} no encontrado."

        try:
            proyecto.crear_tarea_en_historia(story_uuid, tarea, ejecutado_por=user_uuid)
            await repo.save(proyecto)
            return f"Éxito: Tarea '{titulo}' creada con ID: {task_id}."
        except DomainException as e:
            return f"Error de dominio: {e.message}"
        except Exception as e:
            return f"Error inesperado: {str(e)}"


@mcp.tool
async def change_task_status(
    proyecto_id: str,
    tarea_id: str,
    nuevo_estado: Literal["Pendiente", "En Curso", "Bloqueada", "Terminada"],
    ejecutado_por_usuario_id: str
) -> str:
    """
    Cambia el estado de una tarea técnica.
    Requiere ser Developer del proyecto. Si la tarea pasa a 'En Curso',
    el estado de la historia asociada se cambia automáticamente a 'En Progreso'.
    """
    try:
        proj_uuid = uuid.UUID(proyecto_id)
        task_uuid = uuid.UUID(tarea_id)
        user_uuid = uuid.UUID(ejecutado_por_usuario_id)
        state_enum = TaskState(nuevo_estado)
    except ValueError:
        return "Error: IDs inválidos (deben ser UUIDs) o estado no soportado."

    async with ScrumSessionLocal() as session:
        repo = SqliteScrumRepository(session)
        proyecto = await repo.get_by_id(proj_uuid)
        if not proyecto:
            return f"Error: Proyecto con ID {proyecto_id} no encontrado."

        try:
            proyecto.cambiar_estado_tarea(task_uuid, state_enum, ejecutado_por=user_uuid)
            await repo.save(proyecto)
            return f"Éxito: Tarea {tarea_id} cambiada a estado '{nuevo_estado}'."
        except DomainException as e:
            return f"Error de dominio: {e.message}"
        except Exception as e:
            return f"Error inesperado: {str(e)}"


@mcp.tool
async def change_story_status(
    proyecto_id: str,
    story_id: str,
    nuevo_estado: Literal["Nueva", "Refinada", "Comprometida", "En Progreso", "Lista para Pruebas", "Hecha"],
    ejecutado_por_usuario_id: str
) -> str:
    """
    Cambia el estado de una Historia de Usuario.
    Si se cambia a 'Hecha', valida que quien lo ejecute sea el Product Owner
    y que todas las tareas técnicas vinculadas a ella estén en estado 'Terminada'.
    """
    try:
        proj_uuid = uuid.UUID(proyecto_id)
        story_uuid = uuid.UUID(story_id)
        user_uuid = uuid.UUID(ejecutado_por_usuario_id)
        state_enum = StoryState(nuevo_estado)
    except ValueError:
        return "Error: IDs inválidos o estado de historia no soportado."

    async with ScrumSessionLocal() as session:
        repo = SqliteScrumRepository(session)
        proyecto = await repo.get_by_id(proj_uuid)
        if not proyecto:
            return f"Error: Proyecto con ID {proyecto_id} no encontrado."

        try:
            proyecto.cambiar_estado_historia(story_uuid, state_enum, ejecutado_por=user_uuid)
            await repo.save(proyecto)
            return f"Éxito: Historia {story_id} cambiada a estado '{nuevo_estado}'."
        except DomainException as e:
            return f"Error de dominio: {e.message}"
        except Exception as e:
            return f"Error inesperado: {str(e)}"


@mcp.tool
async def close_sprint(
    proyecto_id: str,
    sprint_id: str,
    ejecutado_por_usuario_id: str
) -> str:
    """
    Cierra un Sprint activo, calcula velocidades y desasocia historias sin terminar del Sprint de vuelta al backlog.
    Requiere ser el Scrum Master del proyecto.
    """
    try:
        proj_uuid = uuid.UUID(proyecto_id)
        sprint_uuid = uuid.UUID(sprint_id)
        user_uuid = uuid.UUID(ejecutado_por_usuario_id)
    except ValueError:
        return "Error: IDs inválidos (deben ser UUIDs)."

    async with ScrumSessionLocal() as session:
        repo = SqliteScrumRepository(session)
        proyecto = await repo.get_by_id(proj_uuid)
        if not proyecto:
            return f"Error: Proyecto con ID {proyecto_id} no encontrado."

        try:
            proyecto.cerrar_sprint(sprint_uuid, ejecutado_por=user_uuid)
            await repo.save(proyecto)
            sprint = next(s for s in proyecto.sprints if s.id == sprint_uuid)
            return (
                f"Éxito: Sprint {sprint_id} cerrado. "
                f"Estado: {sprint.estado.value}, "
                f"Velocidad comprometida: {sprint.velocidad_comprometida} pts, "
                f"Velocidad realizada: {sprint.velocidad_realizada} pts."
            )
        except DomainException as e:
            return f"Error de dominio: {e.message}"
        except Exception as e:
            return f"Error inesperado: {str(e)}"


# --- RECURSOS (RESOURCES) ---

@mcp.resource("scrum://docs/architecture")
def get_architecture_docs() -> str:
    """Retorna el documento de arquitectura monolítica modular de la PoC."""
    doc_path = root_path / "01_Documento_PoC_Monolito_Modular.md"
    try:
        with open(doc_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"Error: Archivo {doc_path.name} no encontrado."


@mcp.resource("scrum://docs/domain")
def get_domain_specification() -> str:
    """Retorna la especificación del dominio Scrum de la PoC."""
    doc_path = root_path / "02_Especificación del Dominio.md"
    try:
        with open(doc_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"Error: Archivo {doc_path.name} no encontrado."


@mcp.resource("scrum://docs/deployment")
def get_deployment_guide() -> str:
    """Retorna la guía de despliegue de la PoC."""
    doc_path = root_path / "03_Guía de Despliegue.md"
    try:
        with open(doc_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"Error: Archivo {doc_path.name} no encontrado."


# Crear la aplicación ASGI para despliegues HTTP en la nube (ej. Render, Railway)
# Se ejecuta con: uvicorn src.mcp_server:app --host 0.0.0.0 --port $PORT
app = mcp.http_app()

if __name__ == "__main__":
    # Iniciar servidor MCP en modo stdio (comunicación local estándar)
    mcp.run()
