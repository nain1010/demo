# Bitácora de Sesiones de Trabajo: "Prueba de Concepto - The Hibe"

Este documento registra las sesiones completadas y las tareas realizadas en cada una de ellas para llevar un seguimiento de tu aprendizaje.

---

## 📅 Sesión 1: Shared Kernel (El Núcleo Común)
- [x] **Paso 1.1:** Inicializar la bitácora y la guía de explicación de sesiones.
- [x] **Paso 1.2:** Estudiar los Objetos de Valor (inmutabilidad y validación automática de rango en `DateRange`).
- [x] **Paso 1.3:** Estudiar las Excepciones de dominio (`exceptions.py`) y los Eventos (`events.py`).

---

## 📅 Sesión 2: Dominio de Scrum (Entidades, Agregados y Reglas)
- [x] **Paso 2.1:** Analizar entidades de Scrum (`entities.py` y `value_objects.py`).
- [x] **Paso 2.2:** Estudiar el Agregado Raíz `Proyecto` y sus reglas de negocio (`aggregates.py`).

---

## 📅 Sesión 3: Módulo IdP y Puertos (Abstracciones)
- [x] **Paso 3.1:** Estudiar entidades y roles del IdP (`entities.py`, `value_objects.py`).
- [x] **Paso 3.2:** Analizar el puerto abstracto de identidad (`ports.py`).

---

## 📅 Sesión 4: Persistencia y Adaptadores (Base de Datos)
- [x] **Paso 4.1:** Analizar el adaptador de repositorio SQLite (`sqlite_repository.py`).
- [x] **Paso 4.2:** Estudiar el adaptador HTTP de Supabase (`supabase_adapter.py`).
- [x] **Paso 4.3:** Comprender la inyección de dependencias (`dependencies.py`).

---

## 📅 Sesión 5: Controladores y Capa de Seguridad (Rutas, Middleware y Guards)
- [x] **Paso 5.1:** Estudiar rutas y controladores (`controllers.py`).
- [x] **Paso 5.2:** Analizar el middleware de JWT (`middleware.py`) y los guardianes de roles (`guards.py`).

---

## 📅 Sesión 6: Consistencia Eventual y Pruebas E2E
- [x] **Paso 6.1:** Estudiar el bucle del procesador del Outbox (`outbox_processor.py`).
- [x] **Paso 6.2:** Ejecutar y comprender las pruebas de pytest y el demostrador (`demo_flow.py`).

---

## 📅 Sesión 7: Configuración de Dependencias y Servidor Base MCP (Lectura)
- [x] **Paso 7.1:** Instalar y configurar la dependencia `fastmcp` en el proyecto.
- [x] **Paso 7.2:** Inicializar el servidor MCP en `src/mcp_server.py` y exponer el recurso de documentación.
- [x] **Paso 7.3:** Implementar la herramienta `query_db` para auditoría SQL SELECT de solo lectura.

---

## 📅 Sesión 8: Integración del Dominio y Reglas de Negocio en MCP (Escritura)
- [x] **Paso 8.1:** Integrar las herramientas de escritura en `mcp_server.py` que invocan al agregado raíz `Proyecto`.
- [x] **Paso 8.2:** Implementar el manejo de excepciones `DomainException` para devolver errores de negocio amigables.
- [x] **Paso 8.3:** Verificar el cumplimiento de las invariantes de negocio de Scrum a través del servidor MCP.
