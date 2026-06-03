import httpx
import uuid
import sys
import time
import sys

# Asegurar codificación UTF-8 en consolas de Windows para evitar errores con caracteres especiales
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_URL = "https://the-hibe-api.onrender.com"

# Utilidades para dar formato de consola
def print_header(title):
    print("\n" + "=" * 80)
    print(f"[START] {title}")
    print("=" * 80)

def print_step(step_num, desc):
    print(f"\n* [Paso {step_num}] {desc}...")

def print_success(msg, data=None):
    print(f"  [OK] Exito! {msg}")
    if data:
        print(f"   Datos: {data}")

def print_failure(msg, error=None):
    print(f"  [FAIL] Fallo esperado / Regla de negocio!: {msg}")
    if error:
        print(f"   Detalle: {error}")

async def run_demo():
    print_header("INICIANDO FLUJO DE PRUEBA E2E - THE HIBE (SUPABASE + SCRUM)")
    
    unique_suffix = str(uuid.uuid4())[:8]
    email_admin = f"sm_{unique_suffix}@scrum.com"
    email_po = f"po_{unique_suffix}@scrum.com"
    email_dev = f"dev_{unique_suffix}@scrum.com"
    password = "SuperPassword123!"

    # Instanciar cliente HTTP
    async with httpx.AsyncClient() as client:
        # -------------------------------------------------------------
        print_step(1, "Registrar usuario Scrum Master (Admin global) en Supabase")
        reg_payload = {
            "email": email_admin,
            "password": password,
            "nombre_completo": f"Scrum Master Global {unique_suffix}",
            "rol_global": "Administrador"
        }
        resp = await client.post(f"{BASE_URL}/register", json=reg_payload)
        if resp.status_code != 201:
            print(f"Error al registrar admin: {resp.text}")
            sys.exit(1)
        admin_id = resp.json()["id"]
        print_success("Scrum Master (Admin) registrado", {"id": admin_id, "email": email_admin})

        # -------------------------------------------------------------
        print_step(2, "Registrar usuario Product Owner en Supabase")
        reg_payload_po = {
            "email": email_po,
            "password": password,
            "nombre_completo": f"Product Owner {unique_suffix}",
            "rol_global": "Miembro"
        }
        resp = await client.post(f"{BASE_URL}/register", json=reg_payload_po)
        if resp.status_code != 201:
            print(f"Error al registrar PO: {resp.text}")
            sys.exit(1)
        po_id = resp.json()["id"]
        print_success("Product Owner registrado", {"id": po_id, "email": email_po})

        # -------------------------------------------------------------
        print_step(3, "Registrar usuario Desarrollador en Supabase")
        reg_payload_dev = {
            "email": email_dev,
            "password": password,
            "nombre_completo": f"Dev Team {unique_suffix}",
            "rol_global": "Miembro"
        }
        resp = await client.post(f"{BASE_URL}/register", json=reg_payload_dev)
        if resp.status_code != 201:
            print(f"Error al registrar dev: {resp.text}")
            sys.exit(1)
        dev_id = resp.json()["id"]
        print_success("Desarrollador registrado", {"id": dev_id, "email": email_dev})

        # -------------------------------------------------------------
        print_step(4, "Iniciar sesión con el Scrum Master (Admin)")
        login_resp = await client.post(f"{BASE_URL}/login", json={
            "email": email_admin,
            "password": password
        })
        if login_resp.status_code != 201:
            print(f"Error login admin: {login_resp.text}")
            sys.exit(1)
        admin_token = login_resp.json()["token"]
        headers_admin = {"Authorization": f"Bearer {admin_token}"}
        print_success("Sesión iniciada como SM/Admin (Token JWT obtenido)")

        # -------------------------------------------------------------
        print_step(5, "Iniciar sesión con el Product Owner")
        login_resp_po = await client.post(f"{BASE_URL}/login", json={
            "email": email_po,
            "password": password
        })
        if login_resp_po.status_code != 201:
            print(f"Error login PO: {login_resp_po.text}")
            sys.exit(1)
        po_token = login_resp_po.json()["token"]
        headers_po = {"Authorization": f"Bearer {po_token}"}
        print_success("Sesión iniciada como Product Owner (Token JWT obtenido)")

        # -------------------------------------------------------------
        print_step(6, "Iniciar sesión con el Desarrollador")
        login_resp_dev = await client.post(f"{BASE_URL}/login", json={
            "email": email_dev,
            "password": password
        })
        if login_resp_dev.status_code != 201:
            print(f"Error login dev: {login_resp_dev.text}")
            sys.exit(1)
        dev_token = login_resp_dev.json()["token"]
        headers_dev = {"Authorization": f"Bearer {dev_token}"}
        print_success("Sesión iniciada como Developer (Token JWT obtenido)")

        # -------------------------------------------------------------
        print_step(7, "Crear un nuevo Proyecto (por el Administrador)")
        proj_payload = {
            "nombre": f"Proyecto Hibe Alpha {unique_suffix}",
            "descripcion": "Demo del flujo de Scrum en el Monolito Modular",
            "fecha_inicio": "2026-06-01"
        }
        resp = await client.post(f"{BASE_URL}/projects", json=proj_payload, headers=headers_admin)
        if resp.status_code != 201:
            print(f"Error al crear proyecto: {resp.text}")
            sys.exit(1)
        project_id = resp.json()["id"]
        print_success("Proyecto creado", resp.json())

        # -------------------------------------------------------------
        print_step(8, "Asignar roles de Scrum en el proyecto (Administrador)")
        # Asignar a 'po' como Product Owner
        resp = await client.post(f"{BASE_URL}/projects/{project_id}/members", json={
            "usuario_id": po_id,
            "rol": "Product Owner"
        }, headers=headers_admin)
        print_success("Usuario PO asignado como Product Owner en el proyecto")

        # Asignar a 'admin' como Scrum Master
        resp = await client.post(f"{BASE_URL}/projects/{project_id}/members", json={
            "usuario_id": admin_id,
            "rol": "Scrum Master"
        }, headers=headers_admin)
        print_success("Admin asignado como Scrum Master en el proyecto")

        # Asignar a 'dev' como Developer
        resp = await client.post(f"{BASE_URL}/projects/{project_id}/members", json={
            "usuario_id": dev_id,
            "rol": "Developer"
        }, headers=headers_admin)
        print_success("Usuario Dev asignado como Developer en el proyecto")

        # -------------------------------------------------------------
        print_step(9, "Crear un Sprint en Planificación (Product Owner)")
        sprint_payload = {
            "nombre": "Sprint 1: Cimientos",
            "fecha_inicio": "2026-06-01",
            "fecha_fin": "2026-06-15",
            "objetivo": "Configurar y desplegar la API base"
        }
        resp = await client.post(f"{BASE_URL}/projects/{project_id}/sprints", json=sprint_payload, headers=headers_po)
        if resp.status_code != 201:
            print(f"Error al crear sprint: {resp.text}")
            sys.exit(1)
        sprint_id = resp.json()["id"]
        print_success("Sprint creado en Planificación", resp.json())

        # -------------------------------------------------------------
        print_step(10, "Crear una Historia de Usuario en el Backlog (Product Owner)")
        story_payload = {
            "correlativo": "US-001",
            "titulo": "Autenticación con Supabase",
            "narrativa": "Como usuario quiero registrarme para acceder al sistema",
            "criterios_aceptacion": ["Registra en Supabase", "Genera token JWT"]
        }
        resp = await client.post(f"{BASE_URL}/projects/{project_id}/stories", json=story_payload, headers=headers_po)
        if resp.status_code != 201:
            print(f"Error al crear historia: {resp.text}")
            sys.exit(1)
        story_id = resp.json()["id"]
        print_success("Historia de usuario creada en backlog", resp.json())

        # -------------------------------------------------------------
        print_step(11, "Asociar la Historia de Usuario al Sprint (Planificación por Product Owner)")
        resp = await client.post(f"{BASE_URL}/projects/{project_id}/stories/{story_id}/sprint", json={
            "sprint_id": sprint_id
        }, headers=headers_po)
        if resp.status_code != 201:
            print(f"Error al asociar historia: {resp.text}")
            sys.exit(1)
        print_success("Historia asociada al Sprint (Estado cambiado a Comprometida)")

        # -------------------------------------------------------------
        print_step(12, "Intentar activar el Sprint con la Historia SIN ESTIMAR (Debe Fallar)")
        resp = await client.post(f"{BASE_URL}/projects/{project_id}/sprints/{sprint_id}/activate", headers=headers_admin)
        if resp.status_code == 400:
            print_success("Fallo exitoso debido a regla de negocio", resp.json())
        else:
            print(f"❌ Error: El sprint no debería activarse con historias sin estimar. Status: {resp.status_code}, Res: {resp.text}")
            sys.exit(1)

        # -------------------------------------------------------------
        print_step(13, "Estimar la Historia usando la Escala Fibonacci (Desarrollador)")
        # Estimar con 5 puntos (Valor permitido en Fibonacci)
        resp = await client.post(f"{BASE_URL}/projects/{project_id}/stories/{story_id}/estimate", json={
            "puntos": 5
        }, headers=headers_dev)
        if resp.status_code != 201:
            print(f"Error al estimar historia: {resp.text}")
            sys.exit(1)
        print_success("Historia estimada exitosamente con 5 puntos Fibonacci")

        # -------------------------------------------------------------
        print_step(14, "Activar el Sprint ahora que la historia está estimada (Scrum Master)")
        resp = await client.post(f"{BASE_URL}/projects/{project_id}/sprints/{sprint_id}/activate", headers=headers_admin)
        if resp.status_code != 201:
            print(f"Error al activar sprint: {resp.text}")
            sys.exit(1)
        print_success("Sprint Activado con éxito", resp.json())

        # -------------------------------------------------------------
        print_step(15, "Crear una Tarea Técnica en la Historia (Desarrollador)")
        task_payload = {
            "titulo": "Configurar cliente httpx en el adaptador",
            "descripcion": "Crear llamadas HTTP a la API auth/v1/signup de Supabase"
        }
        resp = await client.post(f"{BASE_URL}/projects/{project_id}/stories/{story_id}/tasks", json=task_payload, headers=headers_dev)
        if resp.status_code != 201:
            print(f"Error al crear tarea: {resp.text}")
            sys.exit(1)
        task_id = resp.json()["id"]
        print_success("Tarea técnica creada en la historia", resp.json())

        # -------------------------------------------------------------
        print_step(16, "Cambiar estado de la Tarea a 'En Curso' (Desarrollador)")
        # Al pasar la primera tarea a En Curso, la historia cambia automáticamente a 'En progreso'
        resp = await client.put(f"{BASE_URL}/projects/{project_id}/tasks/{task_id}/status", json={
            "estado": "En Curso"
        }, headers=headers_dev)
        if resp.status_code != 200:
            print(f"Error al cambiar estado de tarea: {resp.text}")
            sys.exit(1)
        print_success("Tarea iniciada (La Historia de Usuario cambia automáticamente a 'En Progreso')")

        # -------------------------------------------------------------
        print_step(17, "Cambiar estado de la Tarea a 'Terminada' (Desarrollador)")
        resp = await client.put(f"{BASE_URL}/projects/{project_id}/tasks/{task_id}/status", json={
            "estado": "Terminada"
        }, headers=headers_dev)
        if resp.status_code != 200:
            print(f"Error al terminar tarea: {resp.text}")
            sys.exit(1)
        print_success("Tarea finalizada")

        # -------------------------------------------------------------
        print_step(18, "Marcar la Historia de Usuario como 'Hecha' (Product Owner)")
        # Solo el PO puede marcar como Hecha tras evaluar los criterios de aceptación
        resp = await client.put(f"{BASE_URL}/projects/{project_id}/stories/{story_id}/status", json={
            "estado": "Hecha"
        }, headers=headers_po)
        if resp.status_code != 200:
            print(f"Error al marcar historia como hecha: {resp.text}")
            sys.exit(1)
        print_success("Historia de usuario validada y completada (Estado: Hecha)")

        # -------------------------------------------------------------
        print_step(19, "Cerrar el Sprint y Calcular Velocidades (Scrum Master)")
        resp = await client.post(f"{BASE_URL}/projects/{project_id}/sprints/{sprint_id}/close", headers=headers_admin)
        if resp.status_code != 201:
            print(f"Error al cerrar el sprint: {resp.text}")
            sys.exit(1)
        print_success("Sprint cerrado exitosamente", resp.json())
        
        print("\n" + "=" * 80)
        print("[SUCCESS] ¡FLUJO E2E FINALIZADO CON ÉXITO! TODAS LAS REGLAS DE NEGOCIO SE VALIDARON.")
        print("=" * 80)

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_demo())
