# 📅 Sesión 7: Configuración de Dependencias y Servidor Base MCP (Planificación)

En esta sesión vamos a establecer los cimientos del servidor de **Model Context Protocol (MCP)** en nuestro monolito modular. Nos enfocaremos en preparar el entorno e implementar operaciones de solo lectura para auditoría y consulta de datos.

---

## 🎯 Objetivos de la Sesión
1. **Preparar el Entorno:** Instalar la librería `fastmcp` e incorporarla en los requisitos del proyecto.
2. **Crear el Servidor Base:** Implementar la inicialización básica de `FastMCP` en el archivo `src/mcp_server.py`.
3. **Herramienta de Consulta SQL (`query_db`):** Proveer una herramienta que permita al LLM ejecutar consultas SQL SELECT de forma asíncrona sobre la base de datos `scrum.db`.
4. **Exponer Recursos de Arquitectura:** Permitir al LLM leer archivos de documentación directamente mediante URIs de recursos como `scrum://docs/architecture`.

---

## 🛠️ Pasos de Implementación

### Paso 7.1: Dependencias
* Modificar [requirements.txt](file:///c:/PruebaDeConcepto/requirements.txt) para registrar `fastmcp>=0.4.1`.
* Ejecutar la instalación en el entorno virtual (`.venv\Scripts\pip install fastmcp`).

### Paso 7.2: Estructura Inicial del Servidor MCP
* Crear el archivo [mcp_server.py](file:///c:/PruebaDeConcepto/src/mcp_server.py).
* Configurar e instanciar `mcp = FastMCP("Scrum Monolith Assistant")`.
* Configurar el arranque en stdio para su uso local.

### Paso 7.3: Herramienta de Lectura de DB
* Crear la función `query_db(sql_query: str) -> str` decorada con `@mcp.tool`.
* Integrar la sesión asíncrona `SessionLocal` de [database.py](file:///c:/PruebaDeConcepto/src/scrum/infrastructure/database.py#L7) para interactuar de forma segura y no bloqueante con la base de datos SQLite.
* Validar estrictamente que la consulta empiece con `SELECT` para evitar daños accidentales a la integridad de los datos.

### Paso 7.4: Recursos MCP
* Implementar un recurso decorado con `@mcp.resource("scrum://docs/architecture")` que lea y retorne el archivo [01_Documento_PoC_Monolito_Modular.md](file:///c:/PruebaDeConcepto/01_Documento_PoC_Monolito_Modular.md).

---

## 🔍 Criterios de Aceptación y Verificación
* El script debe poder ejecutarse mediante Python (`python src/mcp_server.py`) sin errores de importación.
* Al iniciar, debe quedarse esperando en modo stdio (comportamiento estándar de MCP).
* La herramienta `query_db` debe rechazar sentencias `INSERT`, `UPDATE` o `DELETE`.
