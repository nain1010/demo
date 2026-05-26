import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables desde archivo .env si existe
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

class Config:
    # Proveedor de autenticación: 'supabase' o 'turso'
    AUTH_PROVIDER: str = os.getenv("AUTH_PROVIDER", "turso").lower()

    # Supabase (Auth Cloud)
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")

    # Turso (SQLite en el Edge para Scrum y Auth local)
    # Por defecto usamos un archivo SQLite local asíncrono para pruebas/desarrollo local
    TURSO_DATABASE_URL: str = os.getenv("TURSO_DATABASE_URL", "sqlite+aiosqlite:///scrum.db")
    TURSO_AUTH_TOKEN: str = os.getenv("TURSO_AUTH_TOKEN", "")

    # Para el IdP si se selecciona Turso, podemos usar la misma base de datos o una separada.
    # El requerimiento dice: "Los controladores de datos de un módulo no deben poseer credenciales..."
    # Por simplicidad y separación de celdas física/lógica, usaremos conexiones separadas, 
    # incluso si apuntan al mismo archivo o a uno separado.
    # Para desarrollo local, usaremos archivos SQLite diferentes para simular bases de datos físicamente distintas!
    # Scrum -> scrum.db
    # IdP -> idp.db
    IDP_DATABASE_URL: str = os.getenv("IDP_DATABASE_URL", "sqlite+aiosqlite:///idp.db")

    @classmethod
    def validate(cls):
        if cls.AUTH_PROVIDER not in ["supabase", "turso"]:
            raise ValueError("AUTH_PROVIDER debe ser 'supabase' o 'turso'")
        if cls.AUTH_PROVIDER == "supabase":
            if not cls.SUPABASE_URL or not cls.SUPABASE_KEY:
                raise ValueError("Se requiere SUPABASE_URL y SUPABASE_KEY cuando AUTH_PROVIDER es 'supabase'")
