import pytest
import uuid
from src.idp.domain.value_objects import GlobalRole
from src.idp.infrastructure.adapters.in_memory_adapter import InMemoryIdentityAdapter
from src.shared_kernel.domain.exceptions import BusinessRuleValidationException, UnauthorizedException

@pytest.mark.asyncio
async def test_register_and_authenticate_user():
    adapter = InMemoryIdentityAdapter()
    
    # Registrar un administrador
    user = await adapter.register_user(
        email="admin@test.com",
        password="securepassword",
        nombre_completo="Admin Test",
        rol_global=GlobalRole.ADMINISTRADOR
    )
    assert user.rol_global == GlobalRole.ADMINISTRADOR
    assert user.nombre_completo == "Admin Test"
    
    # Autenticar
    session = await adapter.authenticate(email="admin@test.com", password="securepassword")
    assert session.usuario_id == user.id
    assert session.is_active is True
    assert session.token.startswith("mock-session-token-")
    
    # Validar sesión
    validated_user = await adapter.validate_session(session.token)
    assert validated_user is not None
    assert validated_user.id == user.id

@pytest.mark.asyncio
async def test_register_duplicate_email_fails():
    adapter = InMemoryIdentityAdapter()
    await adapter.register_user(
        email="test@test.com",
        password="pwd",
        nombre_completo="Test",
        rol_global=GlobalRole.MIEMBRO
    )
    
    with pytest.raises(BusinessRuleValidationException) as exc:
        await adapter.register_user(
            email="test@test.com",
            password="pwd2",
            nombre_completo="Test 2",
            rol_global=GlobalRole.MIEMBRO
        )
    assert "El correo electrónico ya está registrado" in str(exc.value)

@pytest.mark.asyncio
async def test_authenticate_invalid_credentials_fails():
    adapter = InMemoryIdentityAdapter()
    await adapter.register_user(
        email="user@test.com",
        password="correct_password",
        nombre_completo="User",
        rol_global=GlobalRole.MIEMBRO
    )
    
    with pytest.raises(UnauthorizedException) as exc:
        await adapter.authenticate(email="user@test.com", password="wrong_password")
    assert "Credenciales inválidas" in str(exc.value)
