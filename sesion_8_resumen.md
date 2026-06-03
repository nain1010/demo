# 📅 Sesión 8: Integración del Dominio y Reglas de Negocio en MCP (Resumen)

En esta sesión conectamos el servidor MCP con el dominio de Scrum, permitiendo que agentes externos interactúen con los sprints, historias de usuario y tareas de manera 100% segura, heredando las validaciones y reglas de negocio del agregado raíz `Proyecto`.

---

## 🛠️ Lo que se hizo en esta Sesión

1. **Implementación de Herramientas de Escritura (Write Tools):**
   * Agregamos herramientas como `create_project`, `assign_project_member`, `create_sprint`, `create_user_story`, `estimate_user_story`, `plan_story_to_sprint`, `activate_sprint`, `create_task_in_story`, `change_task_status`, `change_story_status` y `close_sprint`.
   * Estas herramientas operan cargando y guardando agregados de dominio usando [SqliteScrumRepository](file:///c:/PruebaDeConcepto/src/scrum/infrastructure/adapters/sqlite_repository.py#L20).

2. **Control Seguro de Excepciones:**
   * Envolvimos todas las llamadas del dominio en bloques `try-except DomainException as e`. Esto asegura que los errores metodológicos de Scrum se reporten como texto explicativo amigable para el LLM.

3. **Pruebas de Verificación:**
   * Simulamos llamadas asíncronas para verificar que el agregado controle adecuadamente la exclusividad del Product Owner y Scrum Master y rechace estimaciones fuera de la serie Fibonacci.

---

## 💡 Explicación del Código Implementado

Abre el archivo [src/mcp_server.py](file:///c:/PruebaDeConcepto/src/mcp_server.py). Analicemos el patrón recurrente utilizado para implementar herramientas de escritura seguras:

### El Flujo de Carga - Modificación - Persistencia
Todas las herramientas que modifican datos siguen un proceso de 4 fases consistente:

```python
@mcp.tool
async def estimate_user_story(proyecto_id: str, story_id: str, puntos: int, ejecutado_por_usuario_id: str) -> str:
    # 1. Parsear los datos de entrada
    try:
        proj_uuid = uuid.UUID(proyecto_id)
        story_uuid = uuid.UUID(story_id)
        user_uuid = uuid.UUID(ejecutado_por_usuario_id)
    except ValueError:
        return "Error: IDs inválidos (deben ser UUIDs)."

    # 2. Abrir la sesión asíncrona de base de datos y cargar el Agregado Raíz
    async with ScrumSessionLocal() as session:
        repo = SqliteScrumRepository(session)
        proyecto = await repo.get_by_id(proj_uuid)
        if not proyecto:
            return f"Error: Proyecto con ID {proyecto_id} no encontrado."

        # 3. Invocar la lógica de negocio y guardar cambios
        try:
            proyecto.estimar_historia(story_uuid, puntos, ejecutado_por=user_uuid)
            await repo.save(proyecto)  # Persistencia atómica
            return f"Éxito: Historia {story_id} estimada en {puntos} puntos."
            
        # 4. Capturar errores lógicos de Scrum de forma segura
        except DomainException as e:
            return f"Error de dominio: {e.message}"
```

#### Explicación paso a paso:
* **Fase 1 (Parsing):** El protocolo MCP transfiere datos simples (como strings o ints). Mapeamos estos datos a objetos del dominio de Python, como `uuid.UUID` o `date`, arrojando errores sintácticos rápidos si el formato no es válido.
* **Fase 2 (Carga):** Instanciamos [SqliteScrumRepository](file:///c:/PruebaDeConcepto/src/scrum/infrastructure/adapters/sqlite_repository.py#L20) usando una sesión local asíncrona. Recuperamos la instancia completa del agregado raíz [Proyecto](file:///c:/PruebaDeConcepto/src/scrum/domain/aggregates.py#L8).
* **Fase 3 (Ejecución):** Solicitamos la acción al agregado raíz en memoria (`proyecto.estimar_historia(...)`). Esto ejecuta todas las validaciones (si es developer, si pertenece a la escala Fibonacci, si la historia no está ya hecha). Si todo pasa, delegamos al repositorio la sincronización y guardado mediante `await repo.save(proyecto)`.
* **Fase 4 (Mapeo de Errores):** Si alguna validación de Scrum falla, la capa de dominio lanza una excepción que hereda de `DomainException`. El bloque `except DomainException` la captura y la formatea en un string legible, evitando que la ejecución falle bruscamente y permitiendo que la IA rectifique.

---

## 📝 Ejercicio de Autoevaluación (Sesión 8)

1. **¿Qué pasaría si intentas activar un Sprint que contiene una historia estimación 0 a través de la herramienta `activate_sprint`?**
   * *Respuesta:* El agregado raíz `Proyecto` lanza un error metodológico indicando que historias sin estimar no pueden ingresar a un sprint activo. El servidor captura el error y le responde al modelo `"Error de dominio: Una historia sin estimar (0 puntos) no puede ingresar a un Sprint activo."`.

2. **¿Por qué la arquitectura de adaptadores y repositorios hace tan sencillo crear estas herramientas MCP?**
   * *Respuesta:* Porque toda la complejidad de persistencia (borrar sprints viejos, insertar tareas nuevas, etc.) ya está encapsulada dentro del repositorio del agregado, y toda la seguridad metodológica está encapsulada en el agregado raíz. Crear una herramienta MCP se reduce a una llamada de "cargar, ejecutar y guardar".
