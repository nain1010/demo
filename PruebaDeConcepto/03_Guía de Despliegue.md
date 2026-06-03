# **Guía de Despliegue Automatizado: Litestar \+ Render \+ GitHub**

Este documento especifica los requerimientos técnicos y el flujo de integración continua (CI/CD) para desplegar el backend sin estado (stateless) de la Prueba de Concepto (PoC) basada en el patrón de **Monolito Modular ("The Hibe")**. El despliegue se realiza aprovechando la capa gratuita de **Render** conectada directamente a un repositorio de **GitHub**.

## **1\. Requerimientos de Infraestructura y Preparación**

Antes de iniciar el proceso de despliegue, es necesario contar con los siguientes elementos y configuraciones listos en sus respectivas plataformas:

### **A. Repositorio en GitHub**

* Un repositorio (público o privado) que contenga la estructura del Monolito Modular.  
* El proyecto debe incluir un archivo de definición de dependencias estándar en la raíz (como requirements.txt o pyproject.toml).  
* Un punto de entrada ASGI configurado para levantar la aplicación de Litestar mediante un servidor de producción compatible (por ejemplo, utilizando las instrucciones de ejecución de uvicorn o granian).

### **B. Servicios de Persistencia Externos (Capa Gratuita)**

* **Supabase:** Un proyecto activo con las credenciales de la API de Autenticación (URL del proyecto y la clave pública anónima o clave de servicio).  
* **Turso:** Una base de datos SQLite en el Edge creada con su respectivo token de autenticación y URL de conexión (libsql://...).

### **C. Cuenta en Render**

* Una cuenta activa en Render conectada a la misma cuenta de GitHub que aloja el repositorio del proyecto.

## **2\. Flujo de Configuración: Integración GitHub y Render**

La integración de ambas plataformas permite establecer un canal de entrega continua. A continuación, se detalla el flujo de configuración paso a paso:

\[ Desarrollador \] ───(git push)───\> \[ GitHub Repo \]  
                                           │  
                                    (Webhook Activo)  
                                           ▼  
                                    \[ Render Cloud \]  
                                           │  
                                  (Valida Dependencias)  
                                           ▼  
                                \[ Contenedor Stateless \]

1. **Vinculación de Cuentas (OAuth):**  
   * En el panel de Render, selecciona la creación de un nuevo **Web Service**.  
   * Otorga permisos a la aplicación de Render para acceder a tu cuenta de GitHub y selecciona el repositorio específico de tu PoC.  
2. **Definición de Ajustes Base de Despliegue:**  
   * **Environment (Entorno):** Selecciona Python como motor de ejecución nativo.  
   * **Branch (Rama):** Configura la rama principal (normalmente main o master) como la rama de producción.  
   * **Region:** Elige la región geográfica más cercana a la base de datos de Turso o Supabase para reducir la latencia de red.  
3. **Comandos de Construcción y Arranque:**  
   * **Build Command (Comando de Construcción):** Define la instrucción para actualizar el instalador de paquetes e instalar todas las dependencias del proyecto de forma silenciosa (ej. actualizar pip e instalar los requerimientos del sistema).  
   * **Start Command (Comando de Arranque):** Especifica la instrucción para que el servidor ASGI de producción inicie la aplicación de Litestar en el puerto que Render asigna dinámicamente por defecto.

## **3\. Estrategia de Inyección de Variables de Entorno**

Para garantizar que el backend de Litestar sea completamente agnóstico y pueda conmutar dinámicamente entre el IdP en la nube de Supabase y el IdP local basado en Turso, se deben configurar las siguientes variables de entorno en la sección **Environment** de Render:

| Variable de Entorno | Valores Permitidos | Propósito Técnico |
| :---- | :---- | :---- |
| AUTH\_PROVIDER | supabase / turso | Configura el arranque de la aplicación para que el contenedor de dependencias inyecte el adaptador correspondiente en el puerto IdentityServicePort. |
| SUPABASE\_URL | *URL provista por Supabase* | Endpoint de conexión para el adaptador de identidad en la nube de Supabase. |
| SUPABASE\_KEY | *Clave pública / de servicio* | Credencial de acceso para validar e interactuar con la base de datos de usuarios de Supabase. |
| TURSO\_DATABASE\_URL | *Dirección IP / DNS de Turso* | URL de conexión de la base de datos libSQL para el módulo de Gestión Scrum (y el IdP Propietario si aplica). |
| TURSO\_AUTH\_TOKEN | *Token de acceso de Turso* | Token de autenticación para otorgar permisos de lectura y escritura al backend sobre las tablas de Turso. |

## **4\. Ciclo de Vida del Despliegue Continuo (CI/CD)**

Una vez configurado, el proceso de publicación de cambios se automatiza por completo mediante el siguiente ciclo operativo:

### **A. Auto-despliegue en Render (Auto-Deploy)**

* Cada vez que se realiza un comando git push o se fusiona un cambio en la rama seleccionada de GitHub, Render recibe una notificación mediante un *Webhook* automático.  
* Render inicia un nuevo proceso de construcción: descarga el código actualizado, instala las nuevas dependencias y prepara el entorno.  
* **Despliegue sin Tiempo de Caída (Zero-Downtime Deploy):** Render mantiene la versión anterior de la aplicación funcionando en vivo mientras construye la nueva versión. Solo cuando la nueva versión de Litestar responde exitosamente a las pruebas de salud internas del servidor, Render redirige el tráfico HTTP al nuevo contenedor y apaga el anterior de forma transparente.

### **B. Pruebas de Calidad en Pull Requests (PR Previews)**

* Es recomendable habilitar en Render las "Pull Request Previews". Esto crea un clon temporal y efímero del backend cada vez que se propone un cambio en GitHub.  
* Esta funcionalidad permite probar de forma aislada que las modificaciones no rompan los adaptadores de datos o la configuración del inicio de los plugins antes de incorporar los cambios de manera definitiva a la rama de producción.

## **5\. Gestión Eficiente en la Capa Gratuita (Escenario Multi-PoC)**

Al utilizar la capa gratuita de Render para albergar múltiples proyectos de prueba, se aplican las siguientes reglas de optimización de infraestructura:

* **Gestión de Horas Compartidas:** Render otorga un límite de 750 horas de ejecución gratuita al mes para todos los servicios web de tu cuenta.  
* **Suspensión por Inactividad (Spin-Down):** Si tu aplicación no recibe tráfico HTTP durante 15 minutos continuos, Render suspende de forma temporal el contenedor de Litestar. Durante este periodo de suspensión, el servicio consume 0 horas de tu límite mensual.  
* **Arranque en Frío (Spin-Up):** En el momento en que un cliente o prueba realiza una nueva llamada HTTP al backend, Render inicia nuevamente el contenedor. Este arranque inicial de restauración puede demorar entre 30 y 50 segundos. Una vez encendido, los tiempos de respuesta del backend retornan a la normalidad instantáneamente.

Esta estrategia de suspensión es lo que te permite alojar múltiples proyectos y celdas de prueba concurrentes en una misma cuenta de Render sin agotar jamás tus recursos gratuitos mensuales.

## **6\. Monitoreo Básico de Salud (Health Checks) \[Deseable / Opcional\]**

Para maximizar la resiliencia y el aislamiento durante el flujo de integración continua, se recomienda implementar una ruta de diagnóstico básico dentro de la aplicación.

### **A. El Puerto y Endpoint de Salud**

* **Ruta Dedicada:** Se expone un endpoint público y ligero de diagnóstico (por ejemplo, /health o /status) administrado directamente por el enrutador de Litestar.  
* **Propósito del Diagnóstico:** Este endpoint realiza comprobaciones de conectividad interna sin exponer información sensible:  
  1. Verifica que la conexión con el motor de base de datos de Turso (módulo Scrum) responda exitosamente a una consulta trivial.  
  2. Evalúa si el puerto de identidad configurado (IdentityServicePort) responde correctamente, interactuando con la API de Supabase o la persistencia en Turso según dicte la variable AUTH\_PROVIDER.  
  3. Si todas las dependencias activas responden de manera óptima, el endpoint devuelve un código de estado HTTP 200 (OK). Si alguna conexión clave está caída, responde con un código de error de servidor (ej. HTTP 503 (Service Unavailable)).

### **B. Integración con el Despliegue de Render**

* En la configuración avanzada del Web Service en Render, localiza el campo **Health Check Path** y define la ruta de diagnóstico creada (ej. /health).  
* **Seguridad en la Publicación:** Durante el proceso de *Zero-Downtime Deploy*, Render no direccionará el tráfico de producción al nuevo contenedor de Litestar hasta que este pase con éxito la prueba del Health Check. Si el nuevo código tiene problemas al cargar la inyección de dependencias o falla en conectarse a Turso/Supabase, el despliegue se marcará automáticamente como fallido y el contenedor antiguo (que sigue funcionando de forma segura) se mantendrá en línea. Esto evita que errores de configuración rompan la experiencia de los evaluadores de la PoC.