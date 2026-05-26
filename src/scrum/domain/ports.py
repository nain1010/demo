from abc import ABC, abstractmethod
import uuid
from typing import Optional
from src.scrum.domain.aggregates import Proyecto

class ScrumRepositoryPort(ABC):
    """Puerto de persistencia (Interface) para el agregado Proyecto."""
    
    @abstractmethod
    async def save(self, proyecto: Proyecto) -> None:
        """Guarda o actualiza un Proyecto en la base de datos (incluyendo todos sus Sprints, Historias y Tareas)."""
        pass

    @abstractmethod
    async def get_by_id(self, proyecto_id: uuid.UUID) -> Optional[Proyecto]:
        """Recupera un Proyecto por su ID con todo su estado interno reconstruido."""
        pass
