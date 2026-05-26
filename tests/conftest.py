import sys
import os
from pathlib import Path

# Configurar variables de entorno para pruebas (base de datos en archivos temporales compartidos)
os.environ["TURSO_DATABASE_URL"] = "sqlite+aiosqlite:///scrum_test.db"
os.environ["IDP_DATABASE_URL"] = "sqlite+aiosqlite:///idp_test.db"

# Agregar el directorio raíz del proyecto al PYTHONPATH
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
