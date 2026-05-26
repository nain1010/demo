import pytest
from src.dependencies import provide_identity_service
from src.idp.infrastructure.adapters.turso_adapter import TursoIdentityAdapter
from src.idp.infrastructure.adapters.supabase_adapter import SupabaseIdentityAdapter
from src.config import Config

@pytest.mark.asyncio
async def test_di_resolves_correct_provider():
    # 1. Probar cuando el proveedor es Turso
    Config.AUTH_PROVIDER = "turso"
    service = await provide_identity_service(idp_session=None)  # None es aceptable para construir Turso en este test de tipo
    assert isinstance(service, TursoIdentityAdapter)

    # 2. Probar cuando el proveedor es Supabase
    Config.AUTH_PROVIDER = "supabase"
    Config.SUPABASE_URL = "https://example.supabase.co"
    Config.SUPABASE_KEY = "testkey"
    service = await provide_identity_service(idp_session=None)
    assert isinstance(service, SupabaseIdentityAdapter)
