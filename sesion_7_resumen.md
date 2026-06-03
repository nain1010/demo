# 📅 Sesión 7: Configuración de Dependencias y Servidor Base MCP (Resumen)

En esta sesión hemos implementado la estructura base del servidor de **Model Context Protocol (MCP)**, integrando la biblioteca `FastMCP` en nuestro monolito modular y exponiendo herramientas y recursos de lectura.

---

## 🛠️ Lo que se hizo en esta Sesión

1. **Instalación de Dependencias:**
   * Agregamos `fastmcp>=0.4.1` a [requirements.txt](file:///c:/PruebaDeConcepto/requirements.txt).
   * Instalamos con éxito el paquete en el entorno virtual (`.venv`) del proyecto.

2. **Creación de `mcp_server.py`:**
   * Creamos el archivo [src/mcp_server.py](file:///c:/PruebaDeConcepto/src/mcp_server.py) que actúa como punto de entrada del servidor MCP.
   * Configuramos las herramientas de lectura de base de datos (`query_db` y `get_projects`).
   * Expusimos la documentación técnica del monolito modular como recursos MCP direccionables mediante URIs.

---

## 💡 Explicación del Código Implementado

Abre el archivo [src/mcp_server.py](file:///c:/PruebaDeConcepto/src/mcp_server.py). Analicemos sus piezas clave:

### 1. Preparación del Path de Python y Arranque de FastMCP
```python
import os
import sys
from pathlib import Path

# Asegurar que el directorio raíz del proyecto esté en el path de Python
root_path = Path(__file__).parent.parent.resolve()
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

from fastmcp import FastMCP
mcp = FastMCP("Scrum Monolith Assistant")
```
* **Ruta de Python:** Al ejecutar el servidor MCP desde clientes externos (como Claude Desktop o Cursor), el directorio de trabajo puede no ser la raíz del proyecto. Estas líneas aseguran que Python pueda encontrar y cargar los módulos internos de `src` sin fallos de importación.
* **`FastMCP("Scrum Monolith Assistant")`:** Inicializa el servidor y expone la metadata básica que el cliente LLM leerá durante la fase de negociación inicial del protocolo.

### 2. Herramienta de Consulta SQL (`query_db`)
```python
@mcp.tool
async def query_db(sql_query: str, db_name: Literal["scrum", "idp"] = "scrum") -> str:
    clean_query = sql_query.strip()
    if not clean_query.lower().startswith("select"):
        return "Error: Solo se permiten consultas de lectura (SELECT)."

    session_factory = ScrumSessionLocal if db_name == "scrum" else IdpSessionLocal
    ...
```
* **Decorador `@mcp.tool`:** Registra la función como una herramienta disponible para el LLM. La firma de la función (incluyendo tipos como `Literal` y la descripción en el docstring) se utiliza para autogenerar el esquema JSON-RPC.
* **Control de Seguridad:** Validamos que la consulta comience estrictamente con `SELECT`. Esto impide que el LLM realice acciones destructivas o inserte registros sin respetar las reglas de negocio del dominio.
* **Soporte Multi-base de datos:** Permite alternar dinámicamente entre las bases de datos SQLite físicas de `scrum` e `idp`.
* **Formateo en Markdown:** Los resultados se tabulan automáticamente en Markdown, facilitando que el LLM comprenda la estructura de los datos consultados.

### 3. Exposición de Recursos (Documentation Resources)
```python
@mcp.resource("scrum://docs/architecture")
def get_architecture_docs() -> str:
    ...
```
* **Decorador `@mcp.resource`:** Permite al LLM "leer" archivos del sistema bajo demanda usando un esquema de URI personalizado. Esto evita tener que sobrecargar el contexto inicial del chat, ya que la IA solo descargará la documentación cuando detecte que la necesita para resolver una duda.

---

## 📝 Ejercicio de Autoevaluación (Sesión 7)

1. **¿Por qué la herramienta `query_db` valida que el query empiece con `SELECT` y rechaza otras sentencias?**
   * *Respuesta:* Para proteger la base de datos de modificaciones directas y garantizar que las escrituras solo se hagan invocando a las clases y reglas de negocio del Dominio (Sesión 8).

2. **¿Cuál es la diferencia entre una Tool (Herramienta) y un Resource (Recurso) en el estándar de MCP?**
   * *Respuesta:* Las Tools son verbos (acciones/funciones que el modelo decide ejecutar con parámetros específicos), mientras que los Resources son sustantivos (datos de solo lectura, como archivos de texto o estados estáticos, accesibles mediante URIs).

3. **¿Qué problema de importaciones resuelve el código de manipulación de `sys.path` al inicio de `src/mcp_server.py`?**
   * *Respuesta:* Asegura que al ejecutar el script desde fuera del directorio raíz (por ejemplo, cuando lo invoca Claude Desktop de forma global), Python resuelva correctamente los imports de `src` evitando el error `ModuleNotFoundError`.
