import pytest
import os
import uuid
from datetime import date
from litestar.testing import TestClient
from src.config import Config
from src.dependencies import provide_idp_session, provide_scrum_session
from src.idp.domain.value_objects import GlobalRole
from src.scrum.domain.value_objects import ScrumRole
from src.scrum.infrastructure.database import init_scrum_db, engine as scrum_engine
from src.idp.infrastructure.database import init_idp_db, engine as idp_engine
from src.main import app

import pytest_asyncio
from pathlib import Path

@pytest_asyncio.fixture(autouse=True)
async def setup_e2e_databases():
    # Eliminar archivos anteriores si existen
    for db_file in ["scrum_test.db", "idp_test.db"]:
        path = Path(db_file)
        if path.exists():
            try:
                path.unlink()
            except Exception:
                pass

    # Inicializar bases de datos antes de arrancar la app en E2E
    await init_scrum_db()
    await init_idp_db()
    
    yield
    
    await scrum_engine.dispose()
    await idp_engine.dispose()

    # Eliminar archivos al finalizar
    for db_file in ["scrum_test.db", "idp_test.db"]:
        path = Path(db_file)
        if path.exists():
            try:
                path.unlink()
            except Exception:
                pass

def test_e2e_scrum_flow_and_authorization():
    # Establecer modo local Turso
    Config.AUTH_PROVIDER = "turso"

    with TestClient(app=app) as client:
        # 1. Registrar usuario Administrador global
        reg_resp = client.post(
            "/register",
            json={
                "email": "admin@scrum.com",
                "password": "supersecurepassword",
                "nombre_completo": "Admin Global",
                "rol_global": "Administrador"
            }
        )
        assert reg_resp.status_code == 201
        admin_id = reg_resp.json()["id"]

        # 2. Login de Administrador
        login_resp = client.post(
            "/login",
            json={
                "email": "admin@scrum.com",
                "password": "supersecurepassword"
            }
        )
        assert login_resp.status_code == 201
        admin_token = login_resp.json()["token"]
        headers_admin = {"Authorization": f"Bearer {admin_token}"}

        # 3. Registrar un usuario Miembro
        reg_resp2 = client.post(
            "/register",
            json={
                "email": "member@scrum.com",
                "password": "memberpassword",
                "nombre_completo": "Scrum Member",
                "rol_global": "Miembro"
            }
        )
        assert reg_resp2.status_code == 201
        member_id = reg_resp2.json()["id"]

        # Login del Miembro
        login_resp2 = client.post(
            "/login",
            json={
                "email": "member@scrum.com",
                "password": "memberpassword"
            }
        )
        assert login_resp2.status_code == 201
        member_token = login_resp2.json()["token"]
        headers_member = {"Authorization": f"Bearer {member_token}"}

        # 4. Crear Proyecto (como Administrador)
        proj_resp = client.post(
            "/projects",
            json={
                "nombre": "Proyecto E2E",
                "descripcion": "Descripción del Proyecto",
                "fecha_inicio": "2026-06-01"
            },
            headers=headers_admin
        )
        assert proj_resp.status_code == 201
        project_id = proj_resp.json()["id"]

        # Intentar crear proyecto como Miembro común -> Falla (403 Forbidden)
        proj_resp_fail = client.post(
            "/projects",
            json={
                "nombre": "Proyecto Fallido",
                "descripcion": "Miembro intentando",
                "fecha_inicio": "2026-06-01"
            },
            headers=headers_member
        )
        assert proj_resp_fail.status_code == 403

        # 5. Invitar/Asignar Miembros al Proyecto (como Administrador)
        # Asignar a 'Scrum Member' como Product Owner
        assign_resp = client.post(
            f"/projects/{project_id}/members",
            json={
                "usuario_id": member_id,
                "rol": "Product Owner"
            },
            headers=headers_admin
        )
        assert assign_resp.status_code == 201

        # Asignar a 'Admin Global' como Scrum Master
        assign_resp2 = client.post(
            f"/projects/{project_id}/members",
            json={
                "usuario_id": admin_id,
                "rol": "Scrum Master"
            },
            headers=headers_admin
        )
        assert assign_resp2.status_code == 201

        # 6. Crear Sprint (como Product Owner o Scrum Master) -> Haremos como PO (member)
        sprint_resp = client.post(
            f"/projects/{project_id}/sprints",
            json={
                "nombre": "Sprint 1",
                "fecha_inicio": "2026-06-01",
                "fecha_fin": "2026-06-15",
                "objetivo": "Meta E2E"
            },
            headers=headers_member
        )
        assert sprint_resp.status_code == 201
        sprint_id = sprint_resp.json()["id"]

        # 7. Crear Historia de Usuario (requiere PO -> member)
        story_resp = client.post(
            f"/projects/{project_id}/stories",
            json={
                "correlativo": "US-001",
                "titulo": "Implementar backend",
                "narrativa": "Como dev quiero backend para desplegar",
                "criterios_aceptacion": ["Tests pasan"]
            },
            headers=headers_member
        )
        assert story_resp.status_code == 201
        story_id = story_resp.json()["id"]

        # Asociar historia al sprint
        plan_resp = client.post(
            f"/projects/{project_id}/stories/{story_id}/sprint",
            json={"sprint_id": sprint_id},
            headers=headers_member
        )
        assert plan_resp.status_code == 201

        # Intentar activar el Sprint con historias sin estimar (esfuerzo = 0) -> Falla (400 Bad Request)
        act_resp_fail = client.post(
            f"/projects/{project_id}/sprints/{sprint_id}/activate",
            headers=headers_admin  # Admin es Scrum Master
        )
        # Debe lanzar error por historia sin estimar
        assert act_resp_fail.status_code == 400
        assert "no puede ingresar a un Sprint activo" in act_resp_fail.json()["error"]


def test_e2e_interchangeability():
    # Test de Intercambiabilidad: Turso vs Supabase

    # 1. Caso Turso
    Config.AUTH_PROVIDER = "turso"
    with TestClient(app=app) as client:
        # Registrar y login
        reg_resp = client.post(
            "/register",
            json={
                "email": "interchange@turso.com",
                "password": "secure123password",
                "nombre_completo": "Turso User",
                "rol_global": "Miembro"
            }
        )
        assert reg_resp.status_code == 201
        login_resp = client.post(
            "/login",
            json={"email": "interchange@turso.com", "password": "secure123password"}
        )
        assert login_resp.status_code == 201
        assert "token" in login_resp.json()

    # 2. Caso Supabase
    Config.AUTH_PROVIDER = "supabase"
    Config.SUPABASE_URL = "https://mock.supabase.co"
    Config.SUPABASE_KEY = "mockkey"
    with TestClient(app=app) as client:
        # Registrar y login (debería llamar al adaptador de Supabase y resolverse mediante fallback/simulación)
        reg_resp = client.post(
            "/register",
            json={
                "email": "interchange@supabase.com",
                "password": "secure123password",
                "nombre_completo": "Supabase User",
                "rol_global": "Miembro"
            }
        )
        assert reg_resp.status_code == 201
        login_resp = client.post(
            "/login",
            json={"email": "interchange@supabase.com", "password": "secure123password"}
        )
        assert login_resp.status_code == 201
        assert "token" in login_resp.json()
