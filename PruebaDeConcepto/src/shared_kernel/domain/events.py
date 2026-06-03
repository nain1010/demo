from datetime import datetime, timezone
import uuid
from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass(frozen=True)
class DomainEvent:
    """Clase base inmutable para todos los eventos de dominio."""
    event_id: uuid.UUID = field(default_factory=uuid.uuid4)
    occurred_on: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def event_name(self) -> str:
        """Devuelve el nombre de identificación del evento."""
        return self.__class__.__name__

    def to_dict(self) -> Dict[str, Any]:
        """Convierte el evento a un diccionario para serialización."""
        raise NotImplementedError("Cada evento debe implementar to_dict para ser serializado en la bandeja de salida (Outbox).")
