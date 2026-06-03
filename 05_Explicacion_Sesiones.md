# Guía de Explicación de Sesiones: "The Hibe"

Este documento contiene las explicaciones técnicas detalladas y explicaciones línea por línea del código analizado en cada una de nuestras sesiones de estudio.

---

## 📅 Sesión 1: Shared Kernel (El Núcleo Común)

El **Shared Kernel** (Núcleo Compartido) es el cimiento de nuestra arquitectura. En un monolito modular, las celdas de negocio no deben conocerse directamente para evitar el acoplamiento. Sin embargo, para que el sistema funcione, ambos módulos necesitan hablar el mismo "idioma" básico. Este idioma se define aquí.

Analizaremos las 3 piezas clave de la carpeta [src/shared_kernel/domain/](file:///C:/PruebaDeConcepto/src/shared_kernel/domain/):

### 1. Objetos de Valor (Value Objects)
Abre el archivo [value_objects.py](file:///C:/PruebaDeConcepto/src/shared_kernel/domain/value_objects.py). El código de [DateRange](file:///C:/PruebaDeConcepto/src/shared_kernel/domain/value_objects.py) es el siguiente:

```python
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
```

#### Explicación línea por línea:
* **Línea `@dataclass(frozen=True)`**
  - `@dataclass` es un decorador nativo de Python que nos genera automáticamente funciones estándar como el constructor (`__init__`) y el comparador (`__eq__`).
  - **`frozen=True` (Congelado):** Esto hace que el objeto sea **inmutable**. Una vez creado un rango de fechas, sus atributos (`start_date` y `end_date`) no se pueden modificar. Si intentas cambiarlos, Python lanzará un error. Esto evita que otra parte del código altere accidentalmente las fechas de un sprint activo.
* **Clase [DateRange](file:///C:/PruebaDeConcepto/src/shared_kernel/domain/value_objects.py):**
  - Define nuestro objeto de valor con dos atributos obligatorios del tipo `date` (fecha).
* **Método `__post_init__(self):`**
  - En las `dataclasses`, `__post_init__` se ejecuta automáticamente **justo después** de que el constructor crea el objeto. Aquí es donde colocamos las validaciones.
* **Validaciones de Reglas de Negocio:**
  - Primero, valida que los tipos de datos sean correctos (que sean objetos `date`).
  - Segundo, valida la lógica temporal básica: la fecha de inicio no puede ser mayor que la de fin. Si se intenta crear un rango de fechas inválido (ej: inicio el 15 de junio y fin el 1 de junio), el objeto se niega a existir y lanza un [BusinessRuleValidationException](file:///C:/PruebaDeConcepto/src/shared_kernel/domain/exceptions.py) inmediatamente.
* **`@property` y `duration_days`:**
  - Define una propiedad calculada que devuelve la duración en días simplemente restando las dos fechas.

---

### 2. Excepciones de Dominio (Domain Exceptions)
Abre el archivo [exceptions.py](file:///C:/PruebaDeConcepto/src/shared_kernel/domain/exceptions.py). El código es el siguiente:

```python
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
```

#### Explicación conceptual:
* **[DomainException](file:///C:/PruebaDeConcepto/src/shared_kernel/domain/exceptions.py):** Es la clase madre de nuestros errores de negocio. Hereda de `Exception` de Python.
* **Excepciones Especializadas:** Creamos clases hijas que heredan de [DomainException](file:///C:/PruebaDeConcepto/src/shared_kernel/domain/exceptions.py) (como [EntityNotFoundException](file:///C:/PruebaDeConcepto/src/shared_kernel/domain/exceptions.py) para recursos inexistentes o [BusinessRuleValidationException](file:///C:/PruebaDeConcepto/src/shared_kernel/domain/exceptions.py) para violaciones metodológicas).
* **¿Por qué hacemos esto?**
  - Nos permite separar los errores de código técnico (como fallos de sintaxis o conexión de red) de los **errores lógicos del negocio** (como un sprint mal configurado). 
  - En la Sesión 5 veremos cómo el servidor de Litestar captura estas excepciones de dominio de forma centralizada y las traduce automáticamente a códigos HTTP (400, 404, 401) semánticos para el cliente.

---

### 3. Evento de Dominio (DomainEvent)
Abre el archivo [events.py](file:///C:/PruebaDeConcepto/src/shared_kernel/domain/events.py). El código es el siguiente:

```python
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
```

#### Explicación línea por línea:
* **Decorador `@dataclass(frozen=True)`**
  - Al igual que los Value Objects, los eventos de dominio representan hechos que ya ocurrieron en el pasado, por lo que **deben ser inmutables** (no se pueden alterar una vez creados).
* **Campos `event_id` y `occurred_on`:**
  - Todos los eventos comparten dos atributos base de manera automática:
    - Un identificador único (`event_id`) autogenerado con `uuid.uuid4`.
    - La fecha y hora exacta en formato UTC (`occurred_on`) en la que ocurrió el evento.
  - Usamos `field(default_factory=...)` para que Python genere dinámicamente un nuevo UUID y un nuevo timestamp cada vez que se cree un evento sin necesidad de pasárselos a mano.
* **Propiedad `event_name`:**
  - Propiedad calculada que devuelve el nombre de la clase de evento (ej: si creas una clase hija llamada `UserRegistered`, `event_name` devolverá automáticamente la cadena `"UserRegistered"`).
* **Método `to_dict`:**
  - Define la firma de una función que todas las subclases deben implementar. Como los eventos se guardarán en la base de datos (outbox) en formato JSON, necesitamos convertirlos en diccionarios de Python. Si una clase hija no implementa esta función, lanzará un error de desarrollo (`NotImplementedError`).

---

## 📝 Ejercicio de Autoevaluación (Sesión 1)

Lee el código explicado arriba e intenta responder las siguientes preguntas:

1. **¿Qué pasará si intentamos ejecutar la línea de código `rango = DateRange(date(2026, 6, 15), date(2026, 6, 1))`? ¿Qué excepción lanzará?**
   * *Respuesta del usuario:* un error de que no puede existir por violacion de regla de scrum 

2. **¿Por qué usamos `frozen=True` en la declaración de un Objeto de Valor como `DateRange`?**
   * *Respuesta del usuario:* Para que sea inmutable y no se pueda modificar y que ninguna otra parte del codigo llegue a alterar la fecha.

---

## 📅 Sesión 2: Dominio de Scrum (Entidades, Agregados y Reglas)

En esta sesión estudiaremos el núcleo del negocio: la metodología Scrum plasmada en código limpio. Veremos cómo se definen las entidades de trabajo y cómo el **Agregado Raíz** ([Proyecto](file:///C:/PruebaDeConcepto/src/scrum/domain/aggregates.py)) controla y protege las reglas de negocio del framework.

---

### 1. Enums de Scrum (Value Objects)
Abre el archivo [value_objects.py](file:///C:/PruebaDeConcepto/src/scrum/domain/value_objects.py).
Este archivo contiene simples Enums de Python que limitan los estados y roles que pueden tener los objetos en el dominio:
* **[ScrumRole](file:///C:/PruebaDeConcepto/src/scrum/domain/value_objects.py):** Define los tres roles oficiales del equipo: `PRODUCT_OWNER` (PO), `SCRUM_MASTER` (SM) y `DEVELOPER` (Dev).
* **[SprintState](file:///C:/PruebaDeConcepto/src/scrum/domain/value_objects.py) / [StoryState](file:///C:/PruebaDeConcepto/src/scrum/domain/value_objects.py) / [TaskState](file:///C:/PruebaDeConcepto/src/scrum/domain/value_objects.py):** Definen los ciclos de vida estándar de cada artefacto.

---

### 2. Entidades de Scrum (Sprint, Historias y Tareas)
Abre el archivo [entities.py](file:///C:/PruebaDeConcepto/src/scrum/domain/entities.py).

#### A. Entidad [Sprint](file:///C:/PruebaDeConcepto/src/scrum/domain/entities.py)
```python
class Sprint:
    def __init__(self, id: uuid.UUID, nombre: str, rango_fechas: DateRange, ...):
        self.id = id
        self.nombre = nombre
        self.rango_fechas = rango_fechas
        self.estado = SprintState.PLANIFICACION
        self.velocidad_comprometida = 0
        self.velocidad_realizada = 0
```
* **Qué hace:** Representa un bloque de tiempo de trabajo. 
* **Regla integrada (`actualizar_rango_fechas`):**
  ```python
  def actualizar_rango_fechas(self, nuevo_rango: DateRange):
      if self.estado == SprintState.ACTIVO:
          raise BusinessRuleValidationException("El rango de fechas queda bloqueado y no puede ser modificado una vez el Sprint está Activo.")
      self.rango_fechas = nuevo_rango
  ```
  - Si el Sprint está en desarrollo (`ACTIVO`), el negocio prohíbe mover las fechas. Esta validación se realiza en la misma entidad.

#### B. Entidades [HistoriaUsuario](file:///C:/PruebaDeConcepto/src/scrum/domain/entities.py) y [Tarea](file:///C:/PruebaDeConcepto/src/scrum/domain/entities.py)
* **[HistoriaUsuario](file:///C:/PruebaDeConcepto/src/scrum/domain/entities.py):** Almacena los criterios de aceptación, esfuerzo estimado (en puntos Fibonacci) y el `sprint_id` al que está asociada.
* **[Tarea](file:///C:/PruebaDeConcepto/src/scrum/domain/entities.py):** Representa el trabajo técnico puntual (ej. "crear una tabla en BD"). Contiene su estado (`PENDIENTE`, `EN_CURSO`, `TERMINADA`) y a qué desarrollador está asignada.

---

### 3. El Agregado Raíz: [Proyecto](file:///C:/PruebaDeConcepto/src/scrum/domain/aggregates.py) (Proyecto Core)
Abre el archivo [aggregates.py](file:///C:/PruebaDeConcepto/src/scrum/domain/aggregates.py). 

En el Domain-Driven Design (DDD), un **Agregado** es un clúster de objetos que cambian juntos. Para evitar inconsistencias de datos, el código externo nunca modifica los Sprints o Historias directamente de forma aislada; todo cambio se solicita a la raíz: la clase **[Proyecto](file:///C:/PruebaDeConcepto/src/scrum/domain/aggregates.py)**.

Analicemos las validaciones críticas implementadas en el agregado [Proyecto](file:///C:/PruebaDeConcepto/src/scrum/domain/aggregates.py):

#### A. Gestión de Membresías y Roles
```python
def asignar_rol(self, usuario_id: uuid.UUID, rol: ScrumRole):
    if rol == ScrumRole.PRODUCT_OWNER:
        for uid, r in self.memberships.items():
            if r == ScrumRole.PRODUCT_OWNER and uid != usuario_id:
                raise BusinessRuleValidationException("Ya existe un Product Owner asignado a este proyecto.")
    ...
    self.memberships[usuario_id] = rol
```
* **Qué hace:** Asocia un usuario a un rol Scrum.
* **Regla:** Valida la exclusividad. No permite que se asigne un segundo Product Owner o Scrum Master al mismo proyecto, arrojando una excepción de negocio si se intenta.

#### B. Validación de Fibonacci para Historias
```python
def estimar_historia(self, historia_id: uuid.UUID, puntos: int, ejecutado_por: uuid.UUID):
    self._validar_rol(ejecutado_por, [ScrumRole.DEVELOPER], "Solo los Developers pueden realizar esta acción.")
    if puntos not in [0, 1, 2, 3, 5, 8, 13, 21]:
        raise BusinessRuleValidationException("La estimación debe estar estrictamente en la escala Fibonacci de Scrum (0, 1, 2, 3, 5, 8, 13, 21).")
    ...
```
* **Qué hace:** Permite que los desarrolladores estimen la complejidad.
* **Reglas de Negocio:** 
  1. Primero, valida que quien realiza la acción tenga el rol de `DEVELOPER` en el proyecto.
  2. Segundo, valida que los puntos de historia ingresados pertenezcan estrictamente a la serie Fibonacci permitida.

#### C. Control del Ciclo del Sprint (Activar y Cerrar)
```python
def activar_sprint(self, sprint_id: uuid.UUID, ejecutado_por: uuid.UUID):
    self._validar_rol(ejecutado_por, [ScrumRole.SCRUM_MASTER], "Solo los Scrum Master pueden realizar esta acción.")
    self._validar_roles_minimos()
    
    if any(s.estado == SprintState.ACTIVO for s in self.sprints):
        raise BusinessRuleValidationException("Un Sprint no puede pasar a estado 'Activo' si existe otro Sprint actualmente activo en el mismo Proyecto.")
        
    historias_sprint = [h for h in self.historias_usuario if h.sprint_id == sprint_id]
    if any(h.esfuerzo_estimado == 0 for h in historias_sprint):
        raise BusinessRuleValidationException("Una historia sin estimar (0 puntos) no puede ingresar a un Sprint activo.")
    ...
```
* **Qué hace:** Inicia formalmente un sprint (fase activa).
* **Reglas metodológicas:**
  1. Solo el **Scrum Master** puede activar el sprint.
  2. Valida la exclusividad temporal: No puede haber más de un sprint activo al mismo tiempo en el proyecto.
  3. Valida la estimación: Si el sprint contiene alguna historia sin estimar (esfuerzo = 0), se bloquea la activación.

Al cerrar el sprint (`cerrar_sprint`), el sistema calcula la velocidad real basándose únicamente en las historias que están en estado `HECHA`. Las historias incompletas se "limpian" automáticamente, desasociándose del sprint y regresando a la pila de producto (Backlog) para el siguiente sprint.

#### D. Sincronización Automática de Tareas a Historias
```python
def cambiar_estado_tarea(self, tarea_id: uuid.UUID, nuevo_estado: TaskState, ejecutado_por: uuid.UUID):
    ...
    tarea.estado = nuevo_estado
    
    if nuevo_estado == TaskState.EN_CURSO:
        historia = next((h for h in self.historias_usuario if h.id == tarea.historia_id), None)
        if historia and historia.estado == StoryState.COMPROMETIDA:
            historia.estado = StoryState.EN_PROGRESO
```
* **Qué hace:** Actualiza el estado de una tarea.
* **Regla de arrastre:** Si la tarea pasa a `EN_CURSO`, el dominio busca la historia de usuario padre y actualiza su estado automáticamente a `EN_PROGRESO` sin que el usuario tenga que hacerlo a mano.

---

## 📝 Ejercicio de Autoevaluación (Sesión 2)

Lee el código explicado arriba e intenta responder las siguientes preguntas:

1. **¿Por qué es la clase `Proyecto` (y no `Sprint` ni `HistoriaUsuario`) el Agregado Raíz en este módulo?**
   * *Respuesta del usuario:* es para que no haya inconsistencias de datos, lo que hace es que cambien las dos al mismo tiempo, y es el que autoriza el cambio es la logica de ellas dos.

2. **Si un usuario tiene asignado el rol de `Product Owner` en un proyecto y trata de activar un Sprint, ¿qué error arrojará el sistema y por qué?**
   * *Respuesta del usuario:* error de validacion de negocio, por que solo el scrum master puede activar el sprint.

3. **¿Qué ocurre de forma automática con las Historias de Usuario que quedan incompletas (ej: en estado "En progreso") cuando el Scrum Master cierra un Sprint?**
   * *Respuesta del usuario:* la limpia del sprint y la manda a la pila de producto (Backlog) para el siguiente sprint.

4. **Si creas una tarea técnica en una historia de usuario y la pasas a estado "En Curso", ¿a qué estado cambia automáticamente la Historia de Usuario padre según las reglas del dominio?**
   * *Respuesta del usuario:* en estado en progreso

5. **Si un usuario ya tiene el rol de `Scrum Master` en el proyecto y el administrador intenta asignarle el rol de `Product Owner`, ¿qué pasará en la estructura de `self.memberships` del proyecto? ¿Se guardarán ambos roles o se sobrescribirá?**
   * *Respuesta del usuario:* se sobrescribirá

---

## 📅 Sesión 3: Módulo IdP y Puertos (Abstracciones en la Arquitectura Hexagonal)

En esta sesión estudiaremos el módulo de **Identidad (IdP)** y nos enfocaremos en uno de los conceptos más poderosos de la Arquitectura Hexagonal: **los Puertos**. Entenderemos cómo definir interfaces abstractas que actúen como "enchufe" para conectar posteriormente cualquier base de datos o servicio en la nube de forma intercambiable.

---

### 1. Entidades del IdP (Usuario y Sesión)
Abre el archivo [entities.py](file:///C:/PruebaDeConcepto/src/idp/domain/entities.py).

El dominio del IdP define los objetos necesarios para la autenticación:
* **[User](file:///C:/PruebaDeConcepto/src/idp/domain/entities.py) (Usuario):**
  ```python
  class User:
      def __init__(self, id: uuid.UUID, nombre_completo: str, email: str, rol_global: GlobalRole = GlobalRole.MIEMBRO, ...):
          self.id = id
          self.nombre_completo = nombre_completo
          self.email = email
          self.rol_global = rol_global
  ```
  - Representa al usuario autenticado. Nota que el `rol_global` por defecto es `GlobalRole.MIEMBRO` (que es el rol de menor privilegio).
* **[Session](file:///C:/PruebaDeConcepto/src/idp/domain/entities.py) (Sesión):**
  - Encapsula el token JWT (`token`) generado para un `usuario_id` y si la sesión está activa (`is_active`).

---

### 2. ¿Qué es un Puerto en Arquitectura Hexagonal?
Abre el archivo [ports.py](file:///C:/PruebaDeConcepto/src/idp/domain/ports.py).

En Arquitectura Hexagonal, la capa de dominio **no habla con tecnologías directamente**. No sabe si las contraseñas se guardan en un archivo de texto, en una base de datos local SQLite o en un servicio externo como Supabase Cloud.

Para interactuar con el exterior, el Dominio define un **Puerto**. Un Puerto es una **Interfaz o Clase Abstracta** que actúa como un contrato o especificación. Le dice al mundo exterior: *"No me importa cómo lo hagas, pero necesito que me proveas una clase que implemente estas funciones con estas entradas y salidas"*.

Analicemos la estructura del puerto de identidad [IdentityServicePort](file:///C:/PruebaDeConcepto/src/idp/domain/ports.py):

```python
from abc import ABC, abstractmethod

class IdentityServicePort(ABC):
    """Puerto (Interface) abstracto que define los servicios del IdP."""
    
    @abstractmethod
    async def register_user(self, email: str, password: str, nombre_completo: str, rol_global: GlobalRole) -> User:
        """Registra un nuevo usuario en la base de datos de identidad."""
        pass

    @abstractmethod
    async def authenticate(self, email: str, password: str) -> Session:
        """Autentica a un usuario y genera una sesión activa."""
        pass
    ...
```

#### Explicación técnica:
* **`from abc import ABC, abstractmethod`**
  - `abc` significa **Abstract Base Classes** (Clases Base Abstractas) y es un módulo nativo de Python para programar con interfaces y tipado estricto.
* **Clase [IdentityServicePort(ABC)](file:///C:/PruebaDeConcepto/src/idp/domain/ports.py):**
  - Al heredar de `ABC`, esta clase se vuelve una **Clase Abstracta**. Esto significa que **no puedes instanciarla directamente** en el código (hacer `service = IdentityServicePort()` dará un error de Python). Solo sirve como plantilla base para otras clases que hereden de ella.
* **Decorador `@abstractmethod`**
  - Este decorador le indica a Python que la función de abajo es un método abstracto.
  - **La regla obligatoria:** Cualquier adaptador de infraestructura (como `SupabaseAdapter` o `TursoAdapter`) que herede de esta clase **debe escribir código real** para cada uno de estos métodos abstractos. Si se te olvida implementar alguno de ellos en tu adaptador, Python lanzará una excepción al compilar/arrancar el programa.

---

## 📝 Ejercicio de Autoevaluación (Sesión 3)

Lee la teoría y el código de arriba e intenta responder las siguientes preguntas:

1. **Si intentas instanciar directamente el puerto en tu código haciendo `puerto = IdentityServicePort()`, ¿qué pasará y por qué?**
   * *Respuesta:* [error de python, por que es una clase abstracta]

2. **¿Qué significa el decorador `@abstractmethod` de la librería `abc` de Python y qué obliga a hacer a las clases que heredan de ella?**
   * *Respuesta:* [esun metodo abstracto que obliga a las clases que heredan de ella a implementar todos los metodos abstractos]

3. **En tus propias palabras, ¿cuál es la ventaja de que los controladores del backend consuman el puerto `IdentityServicePort` en lugar de importar directamente una base de datos específica?**
   * *Respuesta:* [ Para que sea mas facil enchufar cualquier servicio de base de datos segun el caso]

4. **¿Qué atributos componen la entidad de dominio `User` en el IdP y cuál es el valor de rol que adquiere por defecto al ser creado?**
   * *Respuesta:* [ Id, Nombre completo, email, admisitrador, password]

5. **Si un programador crea un adaptador llamado `MyCustomIdentityAdapter` que hereda de `IdentityServicePort`, pero se le olvida escribir el método `validate_session`, ¿cuándo y cómo saltará el error en la aplicación?**
   * *Respuesta:* [Al tratar de instanciar la clase]

6. **¿Por qué el módulo IdP tiene su propia entidad `User` en lugar de reutilizar directamente la entidad `Proyecto` o los roles de Scrum?**
   * *Respuesta:* [Por que es otro dominio que no es scrum, es usuario del sistema en general y tiene otros atributos]

7. **En la Arquitectura Hexagonal, ¿qué componente/capa se encarga de implementar los puertos (por ejemplo, escribir el código de acceso a la base de datos o APIs externas)?**
   * *Respuesta:* [ la capa de infraestructura ]

---

## 📅 Sesión 4: Persistencia y Adaptadores (Base de Datos y Supabase)

En esta sesión conectaremos el Dominio con el mundo real mediante los **Adaptadores de Infraestructura**. Analizaremos cómo persistir un Agregado completo de forma atómica en una base de datos local SQLite usando SQLAlchemy asíncrono, cómo consumir APIs de identidad externas (Supabase Auth) y cómo el sistema decide dinámicamente qué adaptador inyectar usando Inyección de Dependencias (DI).

---

### 1. El Adaptador de Repositorio Scrum (SQLite y SQLAlchemy)
Abre el archivo [sqlite_repository.py](file:///C:/PruebaDeConcepto/src/scrum/infrastructure/adapters/sqlite_repository.py).

En el patrón de repositorio para un **Agregado**, la regla de oro es: **Se persiste y se recupera el Agregado completo (Proyecto)**. No se guardan Sprints o Tareas de forma individual y aislada desde fuera.

Analicemos las dos funciones principales del adaptador [SqliteScrumRepository](file:///C:/PruebaDeConcepto/src/scrum/infrastructure/adapters/sqlite_repository.py):

#### A. Guardar el Agregado (`save`)
Para guardar el estado, hacemos un proceso de sincronización (también conocido como **Upsert / Diff**):
1. **Merge del Proyecto:** Registramos o actualizamos el registro base de `ProyectoModel` en la base de datos:
   ```python
   proj_model = ProyectoModel(id=str(proyecto.id), nombre=proyecto.nombre, ...)
   await self.session.merge(proj_model)
   ```
2. **Sincronización de Colecciones (Memberships, Sprints, Historias, Tareas):**
   - Para evitar residuos de datos antiguos, eliminamos de la base de datos aquellos registros que ya no existan en la lista en memoria del Agregado.
   - Por ejemplo, para los Sprints, se borran los de la BD cuyos IDs no estén en `proyecto.sprints`:
     ```python
     await self.session.execute(
         delete(SprintModel).where(
             (SprintModel.proyecto_id == str(proyecto.id)) & (~SprintModel.id.in_(sprint_ids))
         )
     )
     ```
   - Después, recorremos los sprints actuales y los guardamos usando `await self.session.merge(sprint_model)`.
3. **Commit Atómico:** Todo esto corre dentro de la misma transacción de la sesión de SQLAlchemy. Si algo falla, se ejecuta un rollback y la base de datos queda intacta.

#### B. Reconstruir el Agregado (`get_by_id`)
Para cargar el agregado, hacemos el proceso inverso:
1. Consultamos el modelo de `ProyectoModel`.
2. Si existe, instanciamos la clase de dominio `Proyecto`.
3. Consultamos sus memberships, sus sprints, sus historias de usuario y sus tareas mediante sentencias `select` asíncronas filtrando por el ID de proyecto.
4. Poblamos las colecciones internas del objeto `Proyecto` (por ejemplo, `proyecto.sprints.append(sprint)`).
5. Retornamos el objeto `Proyecto` completamente reconstruido y listo para procesar lógica de negocio.

---

### 2. El Adaptador de Identidad (Supabase Auth Cloud)
Abre el archivo [supabase_adapter.py](file:///C:/PruebaDeConcepto/src/idp/infrastructure/adapters/supabase_adapter.py).

Este adaptador implementa [IdentityServicePort](file:///C:/PruebaDeConcepto/src/idp/domain/ports.py) consumiendo el servicio de identidad en la nube de Supabase Auth mediante llamadas HTTP asíncronas con la librería `httpx`.

Analicemos los endpoints que consume:
* **Registro (`register_user`):** Hace un `POST` al endpoint `/auth/v1/signup` enviando el email, password y la metadata adicional (nombre completo y rol global) en el cuerpo JSON.
* **Autenticación (`authenticate`):** Hace un `POST` a `/auth/v1/token?grant_type=password` para validar las credenciales de inicio de sesión y recibir un token JWT firmado de sesión.
* **Validación de Sesión (`validate_session`):** Envía el token JWT recibido en la cabecera `Authorization: Bearer <token>` mediante un `GET` a `/auth/v1/user`. Si Supabase responde `200 OK`, el token es válido y nos devuelve los datos del usuario.
* **Fallback local (`_memory_fallback`):**
  - **Concepto clave:** Para que el proyecto funcione en local, en pruebas E2E o si no hay conexión a internet, el adaptador incluye un diccionario en memoria (`_memory_fallback`). Si las llamadas HTTP a Supabase fallan debido a fallos de red o falta de credenciales, el adaptador intercepta la excepción, guarda el usuario localmente y genera tokens simulados (`mock-supabase-token-`). Esto permite el desarrollo asíncrono sin depender 100% de la nube.

---

### 3. Inyección de Dependencias Dinámica (DI)
Abre el archivo [dependencies.py](file:///C:/PruebaDeConcepto/src/dependencies.py).

¿Cómo sabe la aplicación si debe usar la base de datos de identidad de Supabase o la de desarrollo local? Gracias a la **Inyección de Dependencias**:

```python
async def provide_identity_service(idp_session: AsyncSession) -> IdentityServicePort:
    if Config.AUTH_PROVIDER == "supabase":
        return SupabaseIdentityAdapter(
            supabase_url=Config.SUPABASE_URL,
            supabase_key=Config.SUPABASE_KEY
        )
    else:
        return TursoIdentityAdapter(session=idp_session)
```

* **Qué hace:** Esta función examina el archivo de configuración (`Config.AUTH_PROVIDER`). Si el proveedor configurado es `"supabase"`, instancia el adaptador de la nube. Si no, inyecta la alternativa local ([TursoIdentityAdapter](file:///C:/PruebaDeConcepto/src/idp/infrastructure/adapters/turso_adapter.py)).
* **El contrato:** Observa que ambas ramas del `if` retornan tipos distintos (`SupabaseIdentityAdapter` o `TursoIdentityAdapter`), pero la firma de la función declara que retorna un [IdentityServicePort](file:///C:/PruebaDeConcepto/src/idp/domain/ports.py). Esto es polimorfismo puro. A los controladores no les importa cuál adaptador se instanció; solo interactúan con la interfaz del puerto.

---

## 📝 Ejercicio de Autoevaluación (Sesión 4)

Lee la teoría y el código de arriba e intenta responder las siguientes preguntas:

1. **En la función `save` del repositorio de Scrum, ¿por qué es necesario borrar y volver a insertar elementos (o hacer merge diferido) en lugar de un simple insert para colecciones como `memberships` o `sprints`?**
   * *Respuesta:* [para evitar residuos de datos antiguos, se eliminan de la base de datos aquellos registros que ya no existan en la lista en memoria del Agregado.]

2. **¿Cuál es la función del método `merge()` en SQLAlchemy en comparación con un `add()` tradicional, y por qué se prefiere para los repositorios de agregados?**
   * *Respuesta:* [merge() hace un upsert, es decir, si el registro existe lo actualiza, y si no existe lo inserta. add() solo inserta, si el registro existe lanza un error. se prefiere merge() para los repositorios de agregados porque en este caso los ids son generados aleatoriamente y no sabemos si el registro existe o no]

3. **¿A qué endpoint HTTP y con qué método se envía la solicitud para verificar si un token JWT de sesión sigue siendo válido en Supabase Auth?**
   * *Respuesta:* [GET /auth/v1/user]

4. **¿Por qué el adaptador `SupabaseIdentityAdapter` tiene implementado un diccionario llamado `_memory_fallback`? ¿Qué ventaja aporta al desarrollo de la PoC?**
   * *Respuesta:* [ para que en caso de fallo de red o de otra cosa, tambien se aguarde de forma local, y poder seguir desarrollando sin depender de la nube]

5. **Explica con tus propias palabras qué beneficio aporta el archivo `dependencies.py` al aislar el resto de la aplicación (los controladores de Litestar) de la implementación concreta de la base de datos o el proveedor de autenticación.**
   * *Respuesta:* [ para que pueda usar en la nube con supabaes o local, dependiendo la configuracion]

6. **Si cambias la configuración `Config.AUTH_PROVIDER` a un valor distinto de `"supabase"`, ¿qué adaptador de identidad se inyecta y qué argumento requiere en su constructor?**
   * *Respuesta:* [ TursoIdentityAdapter, requiere de una sesion de sqlalchemy]

---

## 📅 Sesión 5: Controladores y Capa de Seguridad (Rutas, Middleware y Guards)

En esta sesión estudiaremos cómo se exponen nuestras funcionalidades de negocio al exterior mediante la API REST y cómo protegemos cada endpoint. Analizaremos el framework de alto rendimiento **Litestar**, la interceptación de tokens con un **Middleware de ASGI**, y el control de accesos usando **Guardianes (Guards)** basados en el rol global de la plataforma o en el rol asignado en un proyecto de Scrum específico.

---

### 1. El Middleware de Autenticación
Abre el archivo [middleware.py](file:///C:/PruebaDeConcepto/src/shared_kernel/infrastructure/middleware.py).

Un **Middleware** es una capa que intercepta cualquier petición HTTP entrante antes de que llegue a nuestros controladores. Su único trabajo aquí es **identificar al usuario**:

```python
class AuthMiddleware(AbstractMiddleware):
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        ...
        headers = dict(scope.get("headers", []))
        auth_bytes = headers.get(b"authorization", b"")
        auth_header = auth_bytes.decode("utf-8") if auth_bytes else ""

        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                if Config.AUTH_PROVIDER == "supabase":
                    service = await provide_identity_service(None)
                    user = await service.validate_session(token)
                    scope["state"]["user"] = user
                else:
                    async for session in provide_idp_session():
                        service = await provide_identity_service(session)
                        user = await service.validate_session(token)
                        scope["state"]["user"] = user
                        break
            except Exception:
                pass
```

#### Explicación conceptual:
* **Lectura de Cabeceras:** Extrae la cabecera `Authorization` (que viaja como bytes `b"authorization"` en el estándar ASGI) y recupera el token de tipo `Bearer`.
* **Mapeo a Dominio:** Invoca el adaptador de identidad configurado dinámicamente y llama a `validate_session(token)`.
* **Guardado en Request State:** Si el token es válido, inyecta el objeto `User` en `scope["state"]["user"]`. Si el token expiró o es falso, este campo se mantiene en `None`. El middleware no rechaza la petición; solo "identifica" al usuario. La denegación de acceso la harán los **Guards**.

---

### 2. Control de Acceso Mediante Guardianes (Guards)
Abre el archivo [guards.py](file:///C:/PruebaDeConcepto/src/shared_kernel/infrastructure/guards.py).

Un **Guard** en Litestar es una función que se ejecuta antes de resolver una ruta. Si el Guard retorna `None`, la petición continúa; si lanza una excepción (como `NotAuthorizedException` o `PermissionDeniedException`), Litestar interrumpe el flujo y responde al cliente con un código HTTP 401 o 403.

En nuestro backend tenemos tres tipos de guardianes:

#### A. Autenticación Básica (`guard_authenticated`)
Valida simplemente que el usuario no sea anónimo:
```python
def guard_authenticated(connection: ASGIConnection, _: BaseRouteHandler) -> None:
    user = connection.scope.get("state", {}).get("user")
    if not user:
        raise NotAuthorizedException("Debe estar autenticado para realizar esta acción.")
```

#### B. Administrador Global (`guard_admin`)
Valida que el usuario tenga rol de administrador general del sistema (para crear proyectos y asignar miembros):
```python
def guard_admin(connection: ASGIConnection, _: BaseRouteHandler) -> None:
    ...
    if user.rol_global != GlobalRole.ADMINISTRADOR:
        raise PermissionDeniedException("Acción exclusiva para administradores del sistema.")
```

#### C. Rol de Proyecto Scrum Dinámico (`check_project_role`)
Es un guardián dinámico (una función constructora) que valida si el usuario tiene un rol determinado en un proyecto específico. Abre una conexión temporal, consulta el repositorio de persistencia, carga el agregado `Proyecto` mediante el UUID obtenido de la URL de la petición, y verifica los privilegios de membresía:
```python
def check_project_role(allowed_scrum_roles: list[ScrumRole]):
    async def guard(connection: ASGIConnection, _: BaseRouteHandler) -> None:
        ...
        project_id = uuid.UUID(connection.path_params.get("project_id"))
        from src.dependencies import provide_scrum_session, provide_scrum_repository
        async for session in provide_scrum_session():
            repo = await provide_scrum_repository(session)
            proyecto = await repo.get_by_id(project_id)
            ...
            user_role = proyecto.memberships.get(user.id)
            if user_role not in allowed_scrum_roles:
                raise PermissionDeniedException("Permisos insuficientes...")
```

---

### 3. Exposición de Rutas y Controladores
Abre el archivo [controllers.py](file:///C:/PruebaDeConcepto/src/scrum/application/controllers.py).

Los controladores agrupan rutas bajo un prefijo común (ej: `path = "/projects"`). Mapean las peticiones HTTP a llamadas de nuestro Agregado y persisten el resultado.

* **Controller-level Guard:** En `ProjectController` se declara `guards = [guard_authenticated]`. Esto obliga a que **todas** las rutas hijas requieran token de sesión por defecto.
* **Seguridad en Rutas Críticas:**
  - `create_project` y `assign_member` añaden `guards=[guard_admin]` para restringir su uso.
  - `activate_sprint` añade `guards=[check_project_role([ScrumRole.SCRUM_MASTER])]` para asegurar que solo el Scrum Master del proyecto active el sprint.
  - `create_story` añade `guards=[check_project_role([ScrumRole.PRODUCT_OWNER])]` para que solo el PO del proyecto añada historias de usuario.
  - `estimate_story` añade `guards=[check_project_role([ScrumRole.DEVELOPER])]` para que solo los Developers del proyecto estimen los puntos.
* **Seguridad Híbrida (Controlador + Dominio):**
  Observa la ruta `change_story_status`. En el controlador solo pide `guards=[guard_authenticated]`. ¿Por qué? Porque la lógica de quién puede cambiar de estado depende de a qué estado se quiere transicionar:
  - Pasar a `EN_PROGRESO` se hace al activar tareas (Developers).
  - Pasar a `HECHA` (Terminada) requiere autorización exclusiva de `PRODUCT_OWNER` según Scrum.
  Dado que es una regla de negocio dinámica, la validación final se realiza **dentro** del Agregado de Dominio en `proyecto.cambiar_estado_historia(story_id, estado, ejecutado_por=user.id)`.

---

## 📝 Ejercicio de Autoevaluación (Sesión 5)

Lee la teoría y el código de arriba e intenta responder las siguientes preguntas:

1. **¿Qué sucede en el `AuthMiddleware` si un token JWT de sesión es inválido o ha expirado? ¿Interrumpe la llamada retornando un error al cliente o qué acción toma?**
   * *Respuesta:* [Solamente verifica entradas y si no son validas las ignora, y las pasa a los guards. Los guard son los que validan que los tokens sean validos]

2. **¿Cuál es la diferencia de comportamiento entre un código de error HTTP `401 Unauthorized` (NotAuthorizedException) y un `403 Forbidden` (PermissionDeniedException) en nuestra capa de seguridad?**
   * *Respuesta:* [401 es cuando no se proporciona token, y 403 es cuando se proporciona token pero no se tiene permisos para realizar la accion]

3. **¿Cómo extrae el guardián dinámico `check_project_role` el identificador del proyecto (`project_id`) desde la petición HTTP del cliente?**
   * *Respuesta:* [en la url]

4. **En el archivo `controllers.py`, ¿por qué la ruta `change_story_status` no tiene un control de rol específico en la cabecera del decorador del controlador (ej: `guards=[check_project_role(...)]`) y cómo se valida que solo el Product Owner pueda marcar una historia como terminada?**
   * *Respuesta:* [Esta en el agregado de dominio porque es una regla de negocio dinamica]

5. **Si un desarrollador intenta estimar una historia de usuario invocando el endpoint `/projects/{id}/stories/{story_id}/estimate`, ¿qué guardián se activa, qué rol Scrum valida en el proyecto y en qué archivo está declarada esa ruta?**
   * *Respuesta:* [el guards=[check_project_role([ScrumRole.DEVELOPER])]]

---

## 📅 Sesión 6: Consistencia Eventual y Pruebas E2E (Outbox y Flujos Completos)

En esta sesión de cierre estudiaremos cómo mantener la consistencia de datos entre módulos sin acoplarlos físicamente (consistencia eventual) mediante el **Patrón Transactional Outbox**. También repasaremos cómo automatizar y ejecutar pruebas de extremo a extremo (E2E) que simulan el flujo completo de la metodología Scrum.

---

### 1. El Patrón Transactional Outbox (Bandeja de Salida Transaccional)
Abre el archivo [outbox_processor.py](file:///C:/PruebaDeConcepto/src/shared_kernel/infrastructure/outbox_processor.py).

#### ¿Qué problema resuelve?
En nuestro monolito modular, el módulo de **Identidad (IdP)** e **Inicio de Sesión** es independiente del módulo de **Scrum**. Sin embargo, cuando un usuario se registra en el IdP, el módulo Scrum necesita enterarse para guardar una copia local del usuario y poder asignarle roles dentro de los proyectos.

Si intentamos escribir en ambas bases de datos al mismo tiempo dentro de un mismo bloque de código:
1. Escribimos al usuario en el IdP.
2. Hacemos un request o llamada al módulo Scrum.
Si el paso 2 falla (ej. base de datos caída, corte de red), tendríamos un usuario que puede hacer login pero no existe en Scrum. Es una inconsistencia de datos.

#### La solución: Transactional Outbox
En lugar de comunicarlos en caliente, el IdP guarda en su base de datos local el registro del usuario **Y** un registro en una tabla especial llamada `outbox_events` (que contiene el nombre del evento y su payload JSON) de forma **atómica** (en la misma transacción local de base de datos). 

Luego, en segundo plano, un proceso periódico (Worker) lee los eventos de la tabla Outbox y los procesa:

```python
async def process_outbox_events():
    if Config.AUTH_PROVIDER == "supabase":
        # Supabase maneja su propio estado en la nube, no usamos outbox local
        return

    # 1. Leer eventos pendientes del IdP
    async for idp_session in provide_idp_session():
        res = await idp_session.execute(
            select(OutboxEventModel).where(OutboxEventModel.processed == False).order_by(OutboxEventModel.occurred_on)
        )
        events = res.scalars().all()
        if not events:
            return

        # 2. Despachar al módulo Scrum usando la sesión de Scrum
        async for scrum_session in provide_scrum_session():
            scrum_integration = ScrumIntegrationService(scrum_session)
            
            for event in events:
                try:
                    payload = event.payload
                    if event.event_name == "UserRegistered":
                        await scrum_integration.handle_user_registered(
                            user_id=uuid.UUID(payload["id"]),
                            nombre_completo=payload["nombre_completo"],
                            email=payload["email"],
                            rol_global=payload["rol_global"]
                        )
                    elif event.event_name == "UserRoleUpdated":
                        await scrum_integration.handle_user_role_updated(
                            user_id=uuid.UUID(payload["id"]),
                            nuevo_rol=payload["rol_global"]
                        )
                    
                    # 3. Marcar como procesado con éxito
                    event.processed = True
                    await idp_session.commit()
                except Exception as e:
                    await idp_session.rollback()
                    await scrum_session.rollback()
                    return
            break
        break
```

#### Bucle de Procesamiento (`outbox_processor_loop`)
Esta tarea se ejecuta al iniciar la aplicación Litestar en `main.py` de forma asíncrona mediante `asyncio.create_task(outbox_processor_loop(app))`. Ejecuta un bucle infinito que:
1. Llama a `process_outbox_events()`.
2. Espera 5 segundos asíncronamente con `await asyncio.sleep(5)`.
3. Vuelve a empezar.
De este modo, los cambios se propagan de forma **eventual** (con un desfase máximo de 5 segundos), garantizando consistencia a prueba de fallos de red.

---

### 2. Flujo Completo E2E (End-to-End)
Abre el archivo [demo_flow.py](file:///C:/PruebaDeConcepto/demo_flow.py).

Este script simula un ciclo completo de vida de un proyecto Scrum interactuando con la API en producción. Los pasos que realiza son:
1. **Registro:** Crea 3 usuarios en el IdP (Scrum Master/Admin, Product Owner, Developer).
2. **Inicio de Sesión:** Autentica a cada uno para obtener sus respectivos **Tokens JWT** (Bearer tokens).
3. **Creación de Proyecto:** El administrador crea el proyecto `Proyecto Hibe Alpha`.
4. **Asignación de Miembros:** Asocia a los usuarios con sus respectivos roles Scrum en el proyecto.
5. **Planificación (Sprint):** El PO crea un Sprint en estado `PLANIFICACION`.
6. **Planificación (Backlog):** El PO crea una Historia de Usuario en la pila de producto (`US-001`).
7. **Compromiso:** El PO asocia la historia al Sprint.
8. **Validación de Regla de Negocio (Fallo esperado):** El Scrum Master intenta activar el Sprint con la historia sin estimar (esfuerzo = 0). La API arroja un error **400 Bad Request** de forma exitosa protegiendo la metodología.
9. **Estimación:** El Developer estima la historia en 5 puntos Fibonacci.
10. **Activación:** El Scrum Master activa exitosamente el Sprint.
11. **Creación de Tareas:** El Developer crea una tarea técnica y la pasa a estado `En Curso`. La Historia cambia automáticamente a `En Progreso`.
12. **Cierre de Tareas:** El Developer marca la tarea como `Terminada`.
13. **Finalización de Historia:** El PO valida los criterios de aceptación y cambia la historia a `Hecha`.
14. **Cierre de Sprint:** El Scrum Master cierra el Sprint. El sistema calcula la velocidad real basada en historias terminadas y limpia las pendientes enviándolas de vuelta al backlog.

---

## 📝 Ejercicio de Autoevaluación (Sesión 6)

Lee la teoría y el código de arriba e intenta responder las siguientes preguntas:

1. **En tus propias palabras, ¿qué es la consistencia eventual y qué problema evita en un sistema con bases de datos modulares o microservicios?**
   * *Respuesta:* [ es para que los datos esten sincronizados entre los modulos, copiando de idp a scrum ]

2. **¿Por qué el worker del Outbox hace `idp_session.commit()` por cada evento en lugar de hacer un commit general al final de procesar toda la lista de eventos?**
   * *Respuesta:* [Para que no se pierdan datos, si falla en uno no se pierde lo anterior]

3. **Si el bucle del Outbox encuentra que no hay eventos pendientes (`not events`), ¿qué hace el código para evitar un consumo innecesario de recursos de CPU?**
   * *Respuesta:* [Espera 5 segundos y vuelve a empezar]

4. **En el archivo `demo_flow.py`, ¿por qué la primera prueba de activación de Sprint falla con un error de negocio (`400 Bad Request`) y qué regla de la metodología Scrum está protegiendo el sistema en ese paso?**
   * *Respuesta:* [ Falla porque la historia de usuario no tiene estimacion, Proteje que no se pueda ]

5. **Si una Historia de Usuario no se termina durante el Sprint (queda en estado "En progreso"), ¿qué hace el método `close_sprint` del Agregado `Proyecto` con esa historia de usuario y a qué Sprint queda asignada tras el cierre?**
   * *Respuesta:* [ Queda asignada al siguiente sprint o se mueve a la pila de producto ]

---

## 📅 Sesión 7: Configuración de Dependencias y Servidor Base MCP (Lectura)

El **Model Context Protocol (MCP)** es un protocolo abierto que permite a las aplicaciones exponer de forma estandarizada herramientas, recursos y prompts a los LLMs. En esta sesión integramos el framework de Python `FastMCP` para habilitar operaciones de auditoría y lectura de documentación técnica directamente a la IA.

Analizamos el archivo [src/mcp_server.py](file:///C:/PruebaDeConcepto/src/mcp_server.py):

### 1. Herramientas de Consulta SQL de Solo Lectura
```python
@mcp.tool
async def query_db(sql_query: str, db_name: Literal["scrum", "idp"] = "scrum") -> str:
    clean_query = sql_query.strip()
    if not clean_query.lower().startswith("select"):
        return "Error: Solo se permiten consultas de lectura (SELECT)."
    ...
```

#### Explicación conceptual:
* **Decorador `@mcp.tool`:** FastMCP lee automáticamente el nombre de la función, sus argumentos y sus tipados, junto con la descripción de la función, y los exporta como el esquema JSON-RPC que recibe el cliente de IA.
* **Control de Lectura Estricto:** La validación de que el query empiece con `SELECT` es crítica. Evita que la IA ejecute alteraciones directas a la base de datos, las cuales deben pasar obligatoriamente por la lógica y validaciones de los agregados del dominio (Sesión 8).

### 2. Recursos Dinámicos y Estáticos
```python
@mcp.resource("scrum://docs/architecture")
def get_architecture_docs() -> str:
    ...
```
* **Recursos MCP:** Los recursos son como "URIs" o direcciones de solo lectura que el modelo de IA puede resolver bajo demanda. Evitan saturar la ventana de contexto inicial cargando toda la documentación, cargándola únicamente cuando el modelo detecta que es necesario para responder una consulta técnica.

---

## 📝 Ejercicio de Autoevaluación (Sesión 7)

1. **¿Qué sucede si intentas ejecutar la herramienta `query_db` pasando la sentencia `UPDATE proyectos SET nombre = 'Hacked'`?**
   * *Respuesta:* El servidor MCP bloquea la petición inmediatamente respondiendo con un mensaje de error que indica que solo se permiten consultas SELECT.

2. **¿Por qué inyectamos el path raíz en `sys.path` al inicio de `mcp_server.py`?**
   * *Respuesta:* Para que cuando el servidor sea levantado por un proceso externo en otra carpeta (como Claude Desktop), Python pueda resolver las importaciones del paquete `src` sin lanzar `ModuleNotFoundError`.

---

## 📅 Sesión 8: Integración del Dominio y Reglas de Negocio en MCP (Escritura y Acciones)

En esta sesión completamos el servidor MCP integrando herramientas de escritura vinculadas directamente con el agregado raíz [Proyecto](file:///C:/PruebaDeConcepto/src/scrum/domain/aggregates.py#L8). Esto permite al modelo de IA realizar modificaciones sobre sprints, historias y tareas, heredando el 100% de la robustez de las reglas del dominio de Scrum.

Analizamos cómo se estructuraron las herramientas de escritura en [src/mcp_server.py](file:///C:/PruebaDeConcepto/src/mcp_server.py):

### 1. Invocación de Reglas de Negocio en MCP
```python
@mcp.tool
async def assign_project_member(proyecto_id: str, usuario_id: str, rol: Literal["Product Owner", "Scrum Master", "Developer"]) -> str:
    try:
        proj_uuid = uuid.UUID(proyecto_id)
        user_uuid = uuid.UUID(usuario_id)
        scrum_role = ScrumRole(rol)
    except ValueError:
        return "Error: IDs inválidos (deben ser UUIDs) o rol no soportado."

    async with ScrumSessionLocal() as session:
        repo = SqliteScrumRepository(session)
        proyecto = await repo.get_by_id(proj_uuid)
        ...
        try:
            proyecto.asignar_rol(user_uuid, scrum_role)
            await repo.save(proyecto)
            return f"Éxito: Usuario {usuario_id} asignado como '{rol}'..."
        except DomainException as e:
            return f"Error de dominio: {e.message}"
```

#### Explicación conceptual:
* **Uso del Repositorio de Agregado:** La herramienta no escribe consultas directas de inserción en la base de datos. En su lugar, utiliza el repositorio asíncrono [SqliteScrumRepository](file:///C:/PruebaDeConcepto/src/scrum/infrastructure/adapters/sqlite_repository.py#L20) para cargar el agregado en memoria, realiza la operación lógica en el dominio y luego guarda todo el agregado de forma atómica.
* **Captura de Excepciones del Dominio:** Envolver las llamadas en bloques `try-except DomainException as e` nos permite atrapar las violaciones a las reglas de Scrum (como intentar estimar fuera de la escala Fibonacci, o registrar un segundo Scrum Master) y responder con una descripción detallada en lugar de romper el protocolo. Esto le permite al LLM entender qué regla rompió y rectificar sus argumentos de forma autónoma.

---

## 📝 Ejercicio de Autoevaluación (Sesión 8)

1. **Si un LLM intenta llamar a `estimate_user_story` con un valor de estimación de `4`, ¿cuál es el resultado del flujo?**
   * *Respuesta:* El agregado lanza un `BusinessRuleValidationException`, el cual es capturado en el bloque `except DomainException` del servidor MCP y devuelto al LLM como el texto `"Error de dominio: La estimación debe estar estrictamente en la escala Fibonacci de Scrum (0, 1, 2, 3, 5, 8, 13, 21)."`.

2. **¿Por qué es necesario hacer `await repo.save(proyecto)` después de llamar a un método del agregado?**
   * *Respuesta:* Porque el agregado realiza las modificaciones del estado únicamente en la memoria. Para que persistan de forma atómica en SQLite, debemos delegar la sincronización al repositorio.

---

## 🏁 Conclusiones del Aprendizaje (Resumen de Conceptos Clave)

Para finalizar nuestro viaje de estudio por el monolito modular de **"The Hibe"**, aquí tienes una conclusión clave de cada una de las sesiones que analizamos:

### 1. Shared Kernel (El Núcleo Común)
> **Conclusión:** Definir un lenguaje común mediante *Value Objects* inmutables (como [DateRange](file:///C:/PruebaDeConcepto/src/shared_kernel/domain/value_objects.py)) y excepciones de negocio desacopladas ([exceptions.py](file:///C:/PruebaDeConcepto/src/shared_kernel/domain/exceptions.py)) garantiza que todos los módulos de la aplicación puedan comunicarse sin acoplarse físicamente a nivel lógico, permitiendo detectar inconsistencias antes de escribir datos.

### 2. Dominio de Scrum (Entidades y Agregados DDD)
> **Conclusión:** El patrón de *Agregado Raíz* (implementado en [Proyecto](file:///C:/PruebaDeConcepto/src/scrum/domain/aggregates.py)) actúa como un "guardián de la consistencia". Al centralizar cualquier modificación de sprints, historias y tareas a través del agregado raíz, blindamos al sistema contra violaciones de las reglas de negocio (escala Fibonacci, exclusividad de sprints, etc.) desde capas externas.

### 3. Módulo IdP y Puertos (Arquitectura Hexagonal)
> **Conclusión:** Los *Puertos* (como [IdentityServicePort](file:///C:/PruebaDeConcepto/src/idp/domain/ports.py)) son contratos abstractos que aíslan al negocio de la tecnología. Gracias a ellos, el dominio no sabe ni le importa con qué base de datos trabaja o a qué servicio en la nube se conecta, haciendo que el código sea extremadamente fácil de testear mediante dobles de prueba y adaptable al cambio técnico.

### 4. Persistencia y Adaptadores (Repositorios e Infraestructura)
> **Conclusión:** Los *Adaptadores* implementan de forma concreta la comunicación externa. En persistencia, el repositorio del agregado sincroniza de forma atómica todo el árbol de entidades (haciendo merges y eliminando diferencias) para asegurar que el estado de la base de datos coincida perfectamente con el estado en memoria del Agregado, mientras que los fallbacks locales garantizan resiliencia ante cortes de red.

### 5. Controladores y Capa de Seguridad (Litestar, Middleware y Guards)
> **Conclusión:** Separar responsabilidades en la API REST es vital. El *Middleware* identifica pasivamente al usuario decodificando cabeceras JWT, los *Guards* interceptan peticiones estáticas basadas en roles globales o de base de datos, y el *Dominio* realiza el control dinámico final del negocio, logrando un balance ideal entre velocidad de respuesta y seguridad lógica.

### 6. Consistencia Eventual (Transactional Outbox)
> **Conclusión:** Para comunicar módulos independientes de forma segura y sin transacciones distribuidas, el patrón *Transactional Outbox* es el estándar industrial. Al persistir el evento en la base de datos de origen en la misma transacción y procesarlo asíncronamente en segundo plano, garantizamos que los datos se sincronizarán eventualmente sin importar caídas de red o bases de datos temporales.

### 7. Servidor Base MCP (Lectura y Recursos)
> **Conclusión:** El protocolo MCP es un excelente canal de entrada para agentes inteligentes. Implementar herramientas con validaciones sintácticas estrictas (como forzar `SELECT` en queries de BD) y recursos para cargar documentación técnica bajo demanda permite a las IAs auditar el estado del sistema sin poner en riesgo la integridad de los datos.

### 8. Integración del Dominio en MCP (Escritura y Reglas)
> **Conclusión:** Integrar herramientas MCP directamente con los repositorios de agregados y agregados raíces hereda de manera automática todas las validaciones de negocio de la arquitectura limpia. Además, mapear y capturar las excepciones del dominio a mensajes claros permite que el LLM rectifique sus parámetros de forma autónoma ante errores metodológicos.

