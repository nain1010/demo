# **Documento de Especificación: PoC de Monolito Modular con "The Hibe"**

## **1\. Fundamentos y Filosofía de "The Hibe"**

La arquitectura de **"The Hibe" (La Colmena)** organiza el sistema en celdas de negocio herméticas y autónomas. Para esta Prueba de Concepto, el sistema se divide de manera radical, garantizando que cada módulo posea sus propias reglas y persistencia física o lógica, eliminando acoplamientos y permitiendo que la aplicación escale de forma limpia.

### **El Núcleo Compartido (Shared Kernel)**

Para evitar que las celdas dupliquen conceptos estructurales o dependan directamente entre sí, se establece un **Shared Kernel**. Este componente es una biblioteca interna de carácter inmutable que provee la infraestructura base común:

* **Identificadores Únicos:** Estructuras globales para el manejo de identidades de objetos de dominio.  
* **Tipos Primitivos de Dominio:** Objetos de valor transversales (ej. estructuras para correos electrónicos o rangos de fechas).  
* **Contratos de Eventos:** Interfaces de mensajería que unifican el formato de los eventos que viajan entre celdas.  
* **Excepciones Base:** Definiciones estándar para errores de negocio (ej. recurso no encontrado, violación de regla de negocio).

## **2\. Mapa de Dominios (DDD) y Límites de Contexto**

El sistema se delimita en dos contextos acotados principales que operan sobre el Shared Kernel.

                     ┌───────────────────────────┐  
                     │       SHARED KERNEL       │  
                     │ (Tipos, Eventos, Errores) │  
                     └─────────────┬─────────────┘  
                                   │  
            ┌──────────────────────┴──────────────────────┐  
            ▼                                             ▼  
┌───────────────────────┐                     ┌───────────────────────┐  
│     CONTEXTO IDP      │                     │     CONTEXTO SCRUM    │  
│                       │                     │                       │  
│ \- Usuario (Entidad)   │                     │ \- Proyecto (Agregado) │  
│ \- Rol (Value Object)  │                     │ \- Sprint (Agregado)   │  
│ \- Sesión (Entidad)    │                     │ \- Tarea (Entidad)     │  
└───────────────────────┘                     └───────────────────────┘

### **Contexto Acotado: Proveedor de Identidad (IdP)**

Maneja de forma exclusiva la autenticación, creación de cuentas y asignación de roles de usuario en la plataforma.

* **Entidades Principales:** Usuario, Sesión.  
* **Objetos de Valor:** Rol (Administrador, Scrum Master, Product Owner, Equipo de Desarrollo).

### **Contexto Acotado: Gestión de Proyectos Scrum**

Administra la lógica pura del marco de trabajo Scrum. Desconoce cómo se autentica un usuario; solo requiere validar que el identificador del usuario que realiza la acción cuente con los permisos de rol correspondientes dentro del proyecto.

* **Agregados y Entidades:** Proyecto (Raíz del Agregado), Pila de Producto (Product Backlog), Sprint, Historia de Usuario, Tarea.  
* **Objetos de Valor:** Puntos de Historia, Estado del Sprint (Planificación, Activo, Terminado).

## **3\. Arquitectura Hexagonal y el IdP Intercambiable**

Cada celda está estructurada internamente mediante capas de Puertos y Adaptadores. La regla fundamental es que **el Dominio no depende de la tecnología de persistencia ni de los servicios en la nube**.

### **Transparencia en el Proveedor de Identidad**

Para demostrar la flexibilidad de este diseño, el módulo de Gestión de Proyectos interactúa con un puerto abstracto denominado IdentityServicePort. La PoC implementa un mecanismo de intercambio dinámico entre dos proveedores físicos de infraestructura sin alterar una sola línea de la lógica de Scrum:

| Adaptador de Infraestructura | Origen de los Datos | Mecanismo Técnico |
| :---- | :---- | :---- |
| **Adaptador Supabase Auth** | Proveedor en la Nube (Base de datos PostgreSQL externa) | Consume la API de autenticación nativa de Supabase y traduce sus respuestas a objetos de dominio de la PoC. |
| **Adaptador Turso Propietario** | Base de datos SQLite distribuida (Módulo propio) | Realiza consultas directas a las tablas de identidad locales administradas por el propio monolito en Turso. |

### **Orquestación mediante Litestar (Plugins e Inyección)**

* **Registro por Plugins:** Cada módulo se encapsula en un Plugin de Litestar. El plugin lee las variables de entorno del sistema al arrancar el backend.  
* **Inyección Dinámica:** Si la configuración dicta el uso de Supabase, el contenedor de dependencias asocia el IdentityServicePort al adaptador de Supabase. Si se cambia la configuración a Turso, se asocia este último de forma automática. Los controladores y servicios de Scrum consumen el puerto de manera agnóstica.

## **4\. Estrategia Híbrida de Almacenamiento y Persistencia**

La PoC explota al máximo las capas gratuitas de servicios en la nube a través de una división física del almacenamiento:

* **Persistencia del IdP (Supabase \- Capa Gratuita):** Almacena las tablas de autenticación y perfiles utilizando el motor PostgreSQL de Supabase. Aprovecha el límite gratuito de hasta 50,000 usuarios activos mensuales.  
* **Persistencia de Gestión Scrum (Turso \- Capa Gratuita):** Almacena todo el modelo relacional de proyectos, sprints y tareas utilizando libSQL (SQLite en el Edge). Aprovecha el límite gratuito de 5 GB para absorber el alto volumen de lecturas y escrituras transaccionales del día a día del desarrollo de software.

### **Migraciones Descentralizadas e Independientes**

El ciclo de vida de las bases de datos está completamente separado:

* El módulo de IdP contiene sus propios scripts de estructura de datos aplicables únicamente a Supabase (o a sus tablas en Turso si se activa el modo propietario).  
* El módulo Scrum contiene scripts de migración aislados para el motor de Turso. Ningún script altera ni asume la existencia de tablas del otro contexto.

## **5\. Consistencia Eventual mediante el Patrón "Transactional Outbox"**

Al trabajar con dos proveedores de almacenamiento independientes (Supabase y Turso), no es posible ejecutar transacciones ACID globales unificadas. Para asegurar que un cambio en el IdP (como la actualización del rol de un usuario) se refleje correctamente en el módulo de proyectos sin provocar pérdidas de información ante fallas del servidor, se introduce el patrón **Transactional Outbox Local**.

\[ Cambiar Rol de Usuario \]  
           │  
           ▼  
┌──────────────────────────────────────────────┐  
│            TRANSACCIÓN IDP (TURSO)           │  
│                                              │  
│ 1\. Actualiza Tabla \`Usuarios\`                │  
│ 2\. Inserta Evento en Tabla \`Eventos\_Outbox\`  │  
└──────────────────────┬───────────────────────┘  
                       │ (Garantía Atómica)  
                       ▼  
┌──────────────────────────────────────────────┐  
│          BACKGROUND TASK (LITESTAR)          │  
│                                              │  
│ \- Lee periódicamente la tabla \`Eventos\_Outbox\`│  
│ \- Despacha el evento al módulo Scrum         │  
│ \- Marca el evento como "Procesado"           │  
└──────────────────────────────────────────────┘

1. **Escritura Atómica:** Cuando ocurre un cambio en el IdP, el adaptador correspondiente escribe el nuevo estado en la tabla de usuarios y, en la misma transacción de base de datos, inserta un registro en una tabla local llamada Eventos\_Outbox.  
2. **Procesamiento Asíncrono en Litestar:** Utilizando las tareas en segundo plano (*Background Tasks*) de Litestar, un hilo del servidor lee periódicamente la tabla Eventos\_Outbox.  
3. **Despacho Interno:** La tarea toma los eventos pendientes, los envía al puerto de entrada del módulo de Scrum para que actualice sus datos internos y, tras recibir la confirmación de éxito, marca el registro de la bandeja de salida como procesado.

## **6\. Separación Estricta de Requerimientos**

Para facilitar la ejecución del desarrollo guiado por pruebas (TDD), se dividen explícitamente los objetivos del dominio de los de la infraestructura de software.

### **Requerimientos del Dominio (Scrum Core)**

Son las reglas de negocio inalterables que configuran el comportamiento de la metodología Scrum:

* **Ciclo de Vida del Sprint:** Un Sprint no puede pasar a estado "Activo" si existe otro Sprint actualmente activo en el mismo Proyecto. Un Sprint no puede cerrarse si contiene Historias de Usuario pendientes de resolución o que no hayan sido movidas a otra iteración.  
* **Estimación de Esfuerzo:** Las Historias de Usuario deben requerir obligatoriamente una estimación basada estrictamente en la escala de puntos acordada (ej. serie Fibonacci) antes de ser asignadas a un Sprint Activo.  
* **Restricciones de Roles:** Solo los usuarios identificados con el rol de *Product Owner* tienen la facultad de ordenar y priorizar la Pila de Producto. Solo un *Scrum Master* puede dar por iniciado formalmente un Sprint.

### **Requerimientos de la Arquitectura (Infraestructura)**

Son las condiciones técnicas que el Monolito Modular debe cumplir para validar la viabilidad de la solución:

* **Aislamiento de Celdas:** El módulo de Gestión Scrum no debe realizar llamadas de importación de código hacia las capas internas del IdP. Toda comunicación debe ocurrir mediante el paso de los tipos autorizados en el Shared Kernel.  
* **Aislamiento de Persistencia:** Los controladores de datos de un módulo no deben poseer credenciales, conexiones ni privilegios de lectura/escritura sobre el motor de base de datos asignado al módulo contrario.  
* **Resiliencia ante Desconexión:** Si el módulo de Scrum se encuentra fuera de línea o experimenta lentitud, el IdP debe ser capaz de seguir registrando usuarios y autenticando de manera normal, acumulando las notificaciones en la bandeja de salida (Outbox).  
* **Conmutación Transparente:** El intercambio del adaptador del IdP (cambiar de la nube de Supabase a las tablas de Turso) debe realizarse exclusivamente modificando variables de entorno, sin requerir cambios de código ni compilaciones adicionales en el backend.

## **7\. Estrategia de Pruebas Detallada (TDD)**

El enfoque TDD exige escribir las pruebas antes que la lógica de negocio. Gracias a la Arquitectura Hexagonal, la pirámide de pruebas se puede ejecutar con total independencia del estado de los proveedores en la nube.

### **A. Pruebas Unitarias de Dominio (Aisladas de Infraestructura)**

Tienen como objetivo validar el cumplimiento de los **Requerimientos del Dominio (Scrum Core)**.

* **Qué Probar:** \* Intentar activar un Sprint cuando ya existe uno vigente en el modelo del objeto Proyecto (Debe fallar emitiendo una excepción de dominio).  
  * Intentar priorizar la Pila de Producto simulando que la acción es ejecutada por un usuario con rol de *Desarrollador* (Debe fallar bloqueando la acción).  
* **Estrategia Técnica:** Se ejecutan de manera 100% local. El adaptador de persistencia se sustituye por un *Mock* o por un repositorio simulado en memoria que almacena los objetos en listas internas comunes de Python. No hay interacción con bases de datos ni llamadas HTTP. El tiempo de ejecución debe ser de milisegundos.

### **B. Pruebas de Integración de Adaptadores**

Tienen como objetivo validar los contratos de los **Puertos de Salida** con tecnologías reales.

* **Qué Probar:**  
  * Que el adaptador de persistencia de Scrum en Turso guarde adecuadamente un Agregado completo (un Proyecto con tres Sprints estructurados) y logre recuperarlo sin alterar los tipos de datos ni romper las relaciones de herencia de los identificadores.  
  * Que el mecanismo del *Transactional Outbox* guarde y lea correctamente los registros de la tabla de salida de datos ante escenarios de alta concurrencia.  
* **Estrategia Técnica:** Se ejecutan levantando un entorno de pruebas automatizado. Para el módulo Scrum, se inicializa una base de datos local SQLite temporal que emula el comportamiento de Turso. Para el IdP, se puede emplear el emulador local de Supabase basado en contenedores, evitando ensuciar los datos reales de la capa gratuita en la nube.

### **C. Pruebas de Extremo a Extremo (E2E) y de Ciclo de Vida en Litestar**

Tienen como objetivo validar el comportamiento unificado del sistema, los **Hooks**, los **Plugins** y la configuración de **Inversión de Dependencias**.

* **Qué Probar:**  
  * **Validación de Hooks de Entrada:** Emitir una petición HTTP de creación de un Sprint a un endpoint expuesto por Litestar adjuntando un token de sesión simulado. Probar que el *Before Request Hook* intercepte la llamada, invoque correctamente al puerto de identidad activo, extraiga el rol del usuario y permita o deniegue el acceso al controlador web de forma exitosa.  
  * **Prueba de Intercambiabilidad:** Configurar el entorno de pruebas con la bandera de IdP en modo "Supabase" y ejecutar el flujo de login; posteriormente, reiniciar el cliente de pruebas configurando la bandera en modo "Turso" y repetir la llamada. Verificar que el comportamiento de la API web de Litestar responda de manera idéntica y transparente para el usuario final en ambos escenarios.  
* **Estrategia Técnica:** Se utiliza el componente nativo de pruebas de Litestar (TestClient), simulando peticiones sobre el servidor ASGI en proceso para inspeccionar códigos de estado HTTP, cabeceras y respuestas con datos estructurados de extremo a extremo.