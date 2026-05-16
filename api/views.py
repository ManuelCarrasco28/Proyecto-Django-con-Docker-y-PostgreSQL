from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .serializers import EncomiendaTokenSerializer
from .throttles import LoginRateThrottle # <-- NUEVO

from clientes.models import Cliente
from rutas.models import Ruta
from .serializers import ClienteSerializer, RutaSerializer

class EncomiendaTokenView(TokenObtainPairView):
    """
    Vista personalizada para obtener el token JWT.
    Usa un serializer que valida que el usuario sea un empleado activo.
    Incluye throttling para evitar ataques de fuerza bruta.
    """
    throttle_classes = [LoginRateThrottle] # <-- Aplicar throttle de login
    serializer_class = EncomiendaTokenSerializer

class ClienteListView(generics.ListAPIView):
    """
    Lista todos los clientes activos del sistema.
    """
    queryset = Cliente.objects.activos()
    serializer_class = ClienteSerializer
    permission_classes = [IsAuthenticated]

class RutaListView(generics.ListAPIView):
    """
    Lista todas las rutas activas disponibles.
    """
    queryset = Ruta.objects.activas()
    serializer_class = RutaSerializer
    permission_classes = [IsAuthenticated]
