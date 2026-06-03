# 📅 Sesión 8: Integración del Dominio y Reglas de Negocio en MCP (Planificación)

En esta sesión conectaremos el servidor MCP con la lógica de negocio profunda del proyecto. Crearemos herramientas que permitan a un agente de IA interactuar con el dominio de Scrum, asegurando que se validen todas las invariantes y reglas de negocio definidas en la capa de dominio.

---

## 🎯 Objetivos de la Sesión
1. **Herramientas de Escritura de Dominio:** Implementar tools de escritura que utilicen el repositorio [SqliteScrumRepository](file:///c:/PruebaDeConcepto/src/scrum/infrastructure/adapters/sqlite_repository.py#L20) para cargar y guardar los agregados de dominio.
2. **Validación de Reglas de Negocio:** Capturar excepciones del tipo `DomainException` (como `BusinessRuleValidationException` o `EntityNotFoundException`) y devolverlas como mensajes legibles en el servidor MCP en lugar de fallar de manera brusca.
3. **Mapeo de Tipos y Enums:** Traducir los tipos nativos y strings recibidos desde el protocolo MCP a los Value Objects y Enums del dominio (por ejemplo, `ScrumRole`, `SprintState`, `TaskState`, `StoryState` y `date`).
4. **Actualización de Documentación:** Integrar estas nuevas sesiones en la bitácora y guía general del proyecto.

---

## 🛠️ Herramientas a Implementar en `src/mcp_server.py`

* `create_project`: Crea un nuevo proyecto.
* `assign_project_member`: Registra un miembro y su rol en un proyecto (validando la exclusividad de Product Owner y Scrum Master).
* `create_sprint`: Crea un sprint en fase de planificación.
* `create_user_story`: Crea una historia en el backlog (requiere rol de Product Owner).
* `estimate_user_story`: Estima esfuerzo en escala Fibonacci (requiere rol de Developer).
* `plan_story_to_sprint`: Asocia una historia a un sprint de planificación.
* `activate_sprint`: Activa un sprint para comenzar el desarrollo (valida que todas las historias tengan estimación y no haya otro sprint activo).
* `create_task_in_story`: Agrega una tarea técnica a una historia.
* `change_task_status`: Actualiza el estado de una tarea (sincronizando el estado de la historia a "En progreso" si corresponde).
* `close_sprint`: Cierra un sprint calculando la velocidad real lograda y regresando historias incompletas al backlog.

---

## 🔍 Plan de Verificación
* Ejecutar pruebas de importación.
* Verificar de manera simulada que al intentar asignar un segundo Product Owner a un proyecto a través del servidor MCP, el sistema devuelva el mensaje `"Ya existe un Product Owner asignado a este proyecto."` de forma amigable.
* Validar que la escala Fibonacci se mantenga inviolable.
