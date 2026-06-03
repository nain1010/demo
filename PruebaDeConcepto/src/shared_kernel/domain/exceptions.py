class DomainException(Exception):
    """Clase base para todas las excepciones del dominio."""
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class EntityNotFoundException(DomainException):
    """Excepción lanzada cuando un recurso/entidad no es encontrado."""
    pass


class BusinessRuleValidationException(DomainException):
    """Excepción lanzada cuando se viola una regla de negocio."""
    pass


class UnauthorizedException(DomainException):
    """Excepción lanzada cuando una acción no está autorizada para el rol del usuario."""
    pass
