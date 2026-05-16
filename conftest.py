import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from envios.models import Empleado
from envios.tests.factories import UserFactory, EmpleadoFactory

@pytest.fixture
def api_client():
    """Cliente de API sin autenticacion"""
    return APIClient()

@pytest.fixture
def user(db):
    """Usuario de prueba con perfil de empleado activo (usando factories)"""
    user = UserFactory()
    # Crear el perfil de empleado necesario para pasar los permisos EsEmpleadoActivo
    EmpleadoFactory(email=user.email, estado=1) # 1 = Activo
    return user

@pytest.fixture
def auth_client(api_client, user):
    """Cliente de API con JWT valido"""
    refresh = RefreshToken.for_user(user)
    api_client.credentials(
        HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}'
    )
    return api_client
