from dataclasses import dataclass
from datetime import date
from src.shared_kernel.domain.exceptions import BusinessRuleValidationException

@dataclass(frozen=True)
class DateRange:
    start_date: date
    end_date: date

    def __post_init__(self):
        # Asegurarse de que las fechas sean objetos de tipo date
        if not isinstance(self.start_date, date) or not isinstance(self.end_date, date):
            raise BusinessRuleValidationException("Las fechas de inicio y fin deben ser instancias válidas de fecha.")
            
        if self.start_date > self.end_date:
            raise BusinessRuleValidationException("La fecha de inicio no puede ser posterior a la fecha de fin.")

    @property
    def duration_days(self) -> int:
        return (self.end_date - self.start_date).days
