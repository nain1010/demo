# **Especificación Funcional y del Dominio: Gestión de Proyectos Scrum**

Este documento especifica el comportamiento esperado, las reglas de negocio y las restricciones operativas de la Prueba de Concepto (PoC) para la aplicación de gestión de proyectos Scrum. Su propósito es definir con precisión técnica **qué** hace la aplicación y cómo interactúan sus componentes desde la perspectiva del dominio.

## **1\. Módulo de Identidad y Acceso (IdP)**

Este módulo gestiona la autenticación, la seguridad y el control de accesos. Aunque el origen de los datos sea dinámico (Supabase o base de datos propietaria en Turso), el comportamiento funcional para la aplicación de Scrum debe ser idéntico.

### **A. Capacidades del Usuario**

* **Registro e Inicio de Sesión:** Permite a los usuarios crear una cuenta con correo electrónico y contraseña, e iniciar sesión de forma segura para obtener una sesión activa.  
* **Gestión de Perfil Básico:** Cada usuario dispone de un perfil compuesto por su Identificador Único (UUID), Nombre Completo, Correo Electrónico y un Avatar (opcional).

### **B. Roles Globales del Sistema**

El IdP asigna a cada usuario un único rol global que determina sus capacidades iniciales de configuración en el sistema:

* **Administrador:** Puede crear proyectos y dar de alta a nuevos usuarios.  
* **Miembro de Organización:** Usuario general con capacidad de ser invitado a proyectos en roles específicos de Scrum.

## **2\. Módulo de Gestión de Proyectos Scrum**

Este es el núcleo funcional del negocio. Organiza el trabajo en equipos auto-organizados, iteraciones de tiempo limitado (Sprints) y listas priorizadas de requerimientos.

### **A. Gestión de Proyectos (Agregado Raíz: Proyecto)**

Un Proyecto es el contenedor de todas las actividades, Sprints y requerimientos de un producto.

* **Creación de Proyectos:** Un Administrador puede fundar un nuevo proyecto proporcionando un Nombre, una Descripción opcional y una Fecha de Inicio estimada.  
* **Asignación de Roles Scrum:** Dentro de un proyecto, los usuarios deben desempeñar roles específicos del marco de trabajo Scrum. Un mismo usuario puede tener roles diferentes en proyectos diferentes.  
  * **Product Owner (Propietario del Producto):** Máxima autoridad sobre el valor del negocio.  
  * **Scrum Master:** Facilitador del proceso y protector del flujo de trabajo.  
  * **Developers (Equipo de Desarrollo):** Responsables de realizar el trabajo técnico.  
* **Restricción de Membresía:** Un proyecto debe contar obligatoriamente con exactamente un (1) Product Owner y un (1) Scrum Master designados antes de poder planificar o arrancar cualquier Sprint.

### **B. La Pila de Producto (Product Backlog)**

La Pila de Producto es una lista ordenada de todo el trabajo necesario para el desarrollo del proyecto.

#### **Historias de Usuario (User Stories)**

Representan una necesidad del cliente o usuario final que aporta valor de negocio.

* **Atributos Obligatorios:**  
  * Identificador único correlativo (ej. US-001).  
  * Título descriptivo.  
  * Narrativa estándar: *"Como \[Rol\], quiero \[Acción\] para \[Beneficio\]"*.  
  * Criterios de Aceptación (lista de validaciones para dar por completada la historia).  
  * Prioridad (Valor numérico o clasificación).  
  * Esfuerzo Estimado (Puntos de Historia).  
  * Estado (Nueva, Refinada, Comprometida, En Progreso, Lista para Pruebas, Hecha).  
* **Estimación de Esfuerzo (Fibonacci):**  
  El esfuerzo solo se puede estimar utilizando la serie de Fibonacci modificada para Scrum:  
  ![][image1]  
  No se permiten decimales ni valores fuera de esta escala. Una historia sin estimar se considera que tiene un esfuerzo de ![][image2] puntos y no puede ingresar a un Sprint activo.

### **C. Gestión de Sprints (Iteraciones)**

Un Sprint es un bloque de tiempo de duración fija (típicamente entre 1 y 4 semanas) en el cual el equipo se compromete a entregar un incremento de producto potencialmente desplegable.

* **Atributos de un Sprint:**  
  * Nombre (ej. Sprint 1).  
  * Fecha de Inicio y Fecha de Fin (definidas estrictamente en el Shared Kernel como un objeto de valor de rango de fechas).  
  * Objetivo del Sprint (Sprint Goal): Declaración corta de lo que se busca lograr.  
  * Estado (Planificación, Activo, Cerrado).  
* **Reglas Críticas del Ciclo de Vida del Sprint:**  
  1. **Regla de Exclusividad Temporal:** En un proyecto solo puede existir **un (1) único Sprint con estado Activo** a la vez. No se permiten iteraciones paralelas dentro de la misma celda de proyecto.  
  2. **Planificación del Sprint:** Durante la fase de Planificación, el Product Owner y el equipo mueven Historias de Usuario de la Pila de Producto al Sprint Backlog. Al hacerlo, el estado de la historia cambia a Comprometida.  
  3. **Activación del Sprint:** Al pasar el Sprint a estado Activo, el rango de fechas queda bloqueado y no puede ser modificado. La suma de los puntos de historia de las tareas comprometidas define la **Velocidad Comprometida** del Sprint.  
  4. **Cierre del Sprint:** Al cumplirse la fecha de finalización, el Scrum Master debe cerrar el Sprint. El sistema evaluará automáticamente las historias de usuario asociadas:  
     * Las historias en estado Hecha (que cumplen con todos sus criterios de aceptación) computan para la **Velocidad Realizada** del Sprint.  
     * Las historias incompletas se desasocian automáticamente del Sprint cerrado y regresan a la Pila de Producto en estado Nueva o Refinada para ser revaluadas por el Product Owner en la siguiente sesión de refinamiento.

### **D. Gestión de Tareas (Tareas Técnicas)**

Las Tareas son desgloses técnicos de una Historia de Usuario que el Equipo de Desarrollo realiza para completarla.

* **Atributos de la Tarea:**  
  * Título y Descripción Técnica.  
  * Asignado a: Un miembro del Equipo de Desarrollo del proyecto.  
  * Estado (Pendiente, En Curso, Bloqueada, Terminada).  
* **Regla de Cohesión:** Una Tarea no puede existir de forma huérfana; debe estar estrictamente vinculada a una Historia de Usuario padre.  
* **Sincronización de Estados de la Historia:**  
  * Cuando la primera tarea de una historia pasa a En Curso, la Historia de Usuario cambia automáticamente su estado a En Progreso.  
  * Una Historia de Usuario no puede pasar a estado Hecha hasta que **todas sus tareas hijas** se encuentren en estado Terminada y el Product Owner valide el cumplimiento de los Criterios de Aceptación.

## **3\. Matriz de Acciones por Rol Scrum (Autorización)**

El sistema debe validar de manera estricta que solo los usuarios asignados a roles específicos dentro del proyecto puedan ejecutar ciertas operaciones críticas del negocio:

| Operación de Dominio | Administrador | Product Owner | Scrum Master | Developers |
| :---- | :---- | :---- | :---- | :---- |
| Crear Proyecto | **Sí** | No | No | No |
| Invitar Miembros al Proyecto | **Sí** | No | No | No |
| Crear Historias de Usuario | No | **Sí** | No | No |
| Priorizar/Reordenar Pila de Producto | No | **Sí** | No | No |
| Estimar Puntos de Historia | No | No | No | **Sí** |
| Crear y Planificar Sprints | No | **Sí** | **Sí** | No |
| Iniciar / Activar Sprint | No | No | **Sí** | No |
| Crear y Asignar Tareas Técnicas | No | No | No | **Sí** |
| Cambiar Estado de las Tareas | No | No | No | **Sí** |
| Cerrar Sprint | No | No | **Sí** | No |
| Validar Criterios de Aceptación | No | **Sí** | No | No |

## **4\. Flujo Crítico de Ejecución: El Ciclo de un Sprint**

El siguiente flujo describe de manera lógica y secuencial la forma en que los diferentes roles y entidades del dominio interactúan a lo largo del ciclo de vida de un desarrollo Scrum:

\[ Product Owner \] ──( 1\. Prioriza Backlog )──\> \[ Pila de Producto \]  
                                                        │  
\[ Scrum Master \] ───( 2\. Crea Sprint Vacío )────────────┤ (Fase de Planificación)  
                                                        ▼  
\[ Developers \] ─────( 3\. Estima e Incorpora Historias )──\> \[ Sprint Backlog \]  
                                                        │  
\[ Scrum Master \] ───( 4\. Activa el Sprint )─────────────┘ (Fase Activa)  
                                                        │  
                                                        ▼  
\[ Developers \] ─────( 5\. Crean, Asignan y Completan Tareas )  
                                                        │  
                                                        ▼  
\[ Product Owner \] ──( 6\. Aprueba Historias de Usuario )  
                                                        │  
                                                        ▼  
\[ Scrum Master \] ───( 7\. Cierra Sprint )───\> \[ Retorna historias incompletas \]

1. **Fase de Refinamiento:** El Product Owner crea y prioriza las historias en la Pila de Producto. Los Developers evalúan la complejidad asignando puntos de historia en escala Fibonacci (![][image3] a ![][image4]).  
2. **Fase de Planificación:** El Scrum Master crea un nuevo Sprint con estado Planificación y define un rango de fechas válido. El Product Owner arrastra las historias refinadas al Sprint.  
3. **Fase Activa:** El Scrum Master cambia el estado del Sprint a Activo. Se calcula la velocidad comprometida.  
4. **Fase de Ejecución:** Los Developers crean tareas dentro de las historias, se las auto-asignan y modifican sus estados (de Pendiente a En Curso y finalmente a Terminada).  
5. **Fase de Revisión (Review):** El Product Owner evalúa las historias listas y confirma si cumplen con el "Definition of Done" (Criterios de Aceptación). Si es así, las marca como Hechas.  
6. **Fase de Cierre:** El Scrum Master formaliza el fin del Sprint. Las historias completadas computan para la velocidad real. El sistema desplaza de manera automática las historias incompletas de regreso al backlog del proyecto, dejando el sistema en un estado limpio para la planificación de la siguiente iteración.

[image1]: <data:image/png;base64,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>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAoAAAAaCAYAAACO5M0mAAAA5klEQVR4XmNgGEJARkaGU15ePgqIZwFxl6Kiojq6GgYlJSV+oORuIG4WFRXlUVBQMACyrwFxMIpCOTm5cqDgaSAtCBMD8qOB+DrQZHGYIkGQIqApC+E6gUBWVtYUKP4FSPvBdGoC8Vt0hUADjIHiX4G4FUUAl0K4OFDAFyjwn6BCIMeTKIUYAtRQqAQUeI5LIRBXgQVAMQHkHADirUDFHEgKXYBiv0A0su4YIH4ElFCECjEC2c1AfAIUvXCFxsbGrECF04ES+4GmBkAVXQXFOVwREmAE6lYDaggBxq8dSDO6glGAEwAAKX5Nb6tjxO8AAAAASUVORK5CYII=>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAoAAAAaCAYAAACO5M0mAAAAY0lEQVR4XmNgGIJAAQIi0MXBQF5eXhOIs4B4HxD/BSpciK4GDEAKgZIBQNoKiJ/gVAgDQEWSQPxwVCFWQDuFQLwUyGVEl2eQk5NzAUo+AeK/QPwfir8ATb4kIyOji65+FJAPAJ0gLhSrOXDvAAAAAElFTkSuQmCC>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABUAAAAYCAYAAAAVibZIAAABnElEQVR4Xu2TO0sDQRSFN4gg+EI0BhM3s3lgFASVLezETmxEUMHeQjtRC2tLRRtLtVAk4B+wD6TTn6AWSrBTUbAJSPxudjaMg4k2YpMDh7lz75kzc2d2HaeJP0M2m+1KJpPrSqkjz/N20un0EOmIrTOBbh79np2vIpVKjVEsIJrGuIdxlXkZbjl1jNF41O8YzuxaFRQP4YfrunMyF2Pm1/AJjth63/dbyZ/ASiPTAxHAFZnncrlO4iJ8ky5sPZsu6TWluqayczwe7yNskTknHmXBCyxEo9EOU6vblnsfZryva2pCHgxxntM8sGDcrOm298lPMg78aBqLxdoxuhAzFTzAjKNPHoL8AtwkjPzK1IRu7RGey2aS426ZqmM+tW6ZNzSVlihsCCUO85x4W+nXzWQy/cRF6SKk3rQCy/qq1mqmJHwK70KJw7yY6UWHNbGBhiflFC7FGwxPw9YSiUQv4isVfAET9hoBmkFqJZh3vvtBKMzCW4x24TLxJXyVvK0NH1QFf5x0Inz+0n4Ikm1e8Jsu8ihT5v020cQ/4xPQxniTzxofYQAAAABJRU5ErkJggg==>